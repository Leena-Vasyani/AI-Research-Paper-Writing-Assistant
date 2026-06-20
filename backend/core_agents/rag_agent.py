"""
RAG (Retrieval-Augmented Generation) Agent

Production-grade document Q&A with:
- Multi-format ingestion (PDF, DOCX, TXT)
- Hybrid retrieval: FAISS vector search + BM25 keyword search
- Reciprocal Rank Fusion for combining retrieval results
- Conversational memory with full chat history
- Source-attributed answers
- SQLite-backed session persistence
"""

import os
import io
import re
import uuid
import json
import math
import tempfile
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import (
    create_engine,
    Column,
    String,
    Integer,
    DateTime,
    Text,
    ForeignKey,
    inspect,
    text as sa_text,
)
from sqlalchemy.orm import declarative_base, sessionmaker, relationship


# ======================================================================
# Database Models
# ======================================================================

# Keep persistent RAG data at the repository root `data/` directory.
_DB_DIR = Path(__file__).resolve().parents[2] / "data"
_DB_DIR.mkdir(parents=True, exist_ok=True)
_DATABASE_URL = os.getenv(
    "RAG_DATABASE_URL",
    f"sqlite:///{_DB_DIR / 'rag_sessions.db'}",
)

# Persistent vector-store directory so sessions survive server restarts.
_STORE_DIR = Path(os.getenv("RAG_STORE_DIR", str(_DB_DIR / "rag_stores")))
_STORE_DIR.mkdir(parents=True, exist_ok=True)

_Base = declarative_base()
_engine = create_engine(_DATABASE_URL, connect_args={"check_same_thread": False})
_SessionLocal = sessionmaker(bind=_engine)


class RAGChatSession(_Base):
    __tablename__ = "rag_sessions"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False, default="Untitled")
    created_at = Column(DateTime, default=datetime.utcnow)
    last_active = Column(DateTime, default=datetime.utcnow)
    document_count = Column(Integer, default=0)

    messages = relationship(
        "RAGChatMessage",
        back_populates="session",
        cascade="all, delete-orphan",
    )


class RAGChatMessage(_Base):
    __tablename__ = "rag_messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(
        String, ForeignKey("rag_sessions.id", ondelete="CASCADE"), nullable=False
    )
    role = Column(String, nullable=False)  # "user" | "assistant"
    content = Column(Text, nullable=False)
    sources = Column(Text, default="[]")  # JSON list of source references
    created_at = Column(DateTime, default=datetime.utcnow)

    session = relationship("RAGChatSession", back_populates="messages")


_Base.metadata.create_all(_engine)


# ======================================================================
# RAG Agent
# ======================================================================


class RAGAgent:
    """
    Manages document ingestion, hybrid retrieval, and conversational Q&A.

    Each session has its own FAISS vector store in memory and BM25 index.
    """

    def __init__(self, llm_fn=None):
        self._llm = llm_fn or self._default_llm
        # In-memory stores keyed by session_id
        self._vector_stores: Dict[str, Any] = {}
        self._bm25_data: Dict[str, Dict] = {}  # {corpus, bm25}
        self._embeddings = None

    # ------------------------------------------------------------------
    # LLM
    # ------------------------------------------------------------------

    @staticmethod
    def _default_llm(prompt: str, **kwargs) -> str:
        """Fallback LLM using shared llm_provider (Ollama -> Groq -> Gemini)."""
        from core_agents.llm_provider import chat_completion
        
        response = chat_completion(
            prompt,
            max_tokens=kwargs.get("max_tokens", 1500),
            temperature=kwargs.get("temperature", 0.2),
        )
        if not response:
            raise RuntimeError("All LLM providers failed to generate a response.")
        return response

    def _chat(self, prompt: str, **kwargs) -> str:
        return self._llm(prompt, **kwargs)

    # ------------------------------------------------------------------
    # Embeddings (lazy singleton)
    # ------------------------------------------------------------------

    def _get_embeddings(self):
        if self._embeddings is None:
            from langchain_huggingface import HuggingFaceEmbeddings

            self._embeddings = HuggingFaceEmbeddings(
                model_name="all-MiniLM-L6-v2",
                model_kwargs={"device": "cpu"},
                encode_kwargs={"normalize_embeddings": True},
            )
        return self._embeddings

    # ------------------------------------------------------------------
    # Persistence (so sessions survive server restarts)
    # ------------------------------------------------------------------

    @staticmethod
    def _store_path(session_id: str) -> Path:
        return _STORE_DIR / session_id

    def _persist(self, session_id: str) -> None:
        """Save this session's FAISS index + chunk corpus to disk."""
        try:
            path = self._store_path(session_id)
            path.mkdir(parents=True, exist_ok=True)
            store = self._vector_stores.get(session_id)
            if store is not None:
                store.save_local(str(path / "faiss"))
            corpus_docs = self._bm25_data.get(session_id, {}).get("corpus_docs", [])
            chunks = [
                {"page_content": d.page_content, "metadata": d.metadata}
                for d in corpus_docs
            ]
            with open(path / "chunks.json", "w", encoding="utf-8") as f:
                json.dump(chunks, f)
        except Exception as e:
            print(f"   [!] Failed to persist RAG store for {session_id}: {e}")

    def _ensure_loaded(self, session_id: str) -> bool:
        """Load a session's FAISS + BM25 from disk if not already in memory."""
        if session_id in self._vector_stores:
            return True
        faiss_dir = self._store_path(session_id) / "faiss"
        if not faiss_dir.exists():
            return False
        try:
            from langchain_community.vectorstores import FAISS
            from langchain_core.documents import Document

            embeddings = self._get_embeddings()
            self._vector_stores[session_id] = FAISS.load_local(
                str(faiss_dir), embeddings, allow_dangerous_deserialization=True
            )
            chunks_file = self._store_path(session_id) / "chunks.json"
            if chunks_file.exists():
                with open(chunks_file, "r", encoding="utf-8") as f:
                    raw = json.load(f)
                docs = [
                    Document(page_content=c["page_content"], metadata=c.get("metadata", {}))
                    for c in raw
                ]
                self._bm25_data[session_id] = {}
                self._rebuild_bm25(session_id, docs)
            return True
        except Exception as e:
            print(f"   [!] Failed to load RAG store for {session_id}: {e}")
            return False

    # ------------------------------------------------------------------
    # Follow-up question contextualization
    # ------------------------------------------------------------------

    @staticmethod
    def _contextualize_query(question: str, recent_history: List[Dict[str, Any]]) -> str:
        """Expand a short / pronoun-y follow-up into a standalone retrieval query
        by prepending the previous user turn. Cheap (no extra LLM call)."""
        q = (question or "").strip()
        if not recent_history:
            return q
        lowered = q.lower()
        is_followup = len(q.split()) <= 6 or bool(
            re.match(
                r"^(it|its|they|them|that|this|these|those|he|she|"
                r"what about|and |also|why|how|tell me more|explain|more)\b",
                lowered,
            )
        )
        if not is_followup:
            return q
        last_user = ""
        for msg in reversed(recent_history):
            if msg.get("role") == "user":
                last_user = msg.get("content", "")
                break
        return f"{last_user} {q}".strip() if last_user else q

    # ------------------------------------------------------------------
    # Session management
    # ------------------------------------------------------------------

    def create_session(self, name: Optional[str] = None) -> Dict[str, Any]:
        """Create a new chat session."""
        db = _SessionLocal()
        try:
            count = db.query(RAGChatSession).count()
            session_id = str(uuid.uuid4())
            session = RAGChatSession(
                id=session_id,
                name=name or f"Chat {count + 1}",
            )
            db.add(session)
            db.commit()
            return {
                "session_id": session_id,
                "name": session.name,
                "created_at": session.created_at.isoformat() if session.created_at else "",
            }
        finally:
            db.close()

    def list_sessions(self) -> List[Dict[str, Any]]:
        """List all chat sessions, newest first."""
        db = _SessionLocal()
        try:
            sessions = (
                db.query(RAGChatSession)
                .order_by(RAGChatSession.last_active.desc())
                .all()
            )
            return [
                {
                    "id": s.id,
                    "name": s.name,
                    "created_at": s.created_at.isoformat() if s.created_at else "",
                    "last_active": s.last_active.isoformat() if s.last_active else "",
                    "document_count": s.document_count or 0,
                }
                for s in sessions
            ]
        finally:
            db.close()

    def get_messages(self, session_id: str) -> List[Dict[str, Any]]:
        """Get chat history for a session."""
        db = _SessionLocal()
        try:
            msgs = (
                db.query(RAGChatMessage)
                .filter(RAGChatMessage.session_id == session_id)
                .order_by(RAGChatMessage.created_at)
                .all()
            )
            return [
                {
                    "role": m.role,
                    "content": m.content,
                    "sources": json.loads(m.sources) if m.sources else [],
                    "created_at": m.created_at.isoformat() if m.created_at else "",
                }
                for m in msgs
            ]
        finally:
            db.close()

    def delete_session(self, session_id: str) -> bool:
        """Delete a session and all its messages."""
        db = _SessionLocal()
        try:
            session = db.query(RAGChatSession).filter(
                RAGChatSession.id == session_id
            ).first()
            if not session:
                return False
            db.delete(session)
            db.commit()
            # Clean up in-memory stores
            self._vector_stores.pop(session_id, None)
            self._bm25_data.pop(session_id, None)
            # Clean up persisted store on disk
            try:
                import shutil
                store_path = self._store_path(session_id)
                if store_path.exists():
                    shutil.rmtree(store_path, ignore_errors=True)
            except Exception:
                pass
            return True
        finally:
            db.close()

    def _save_message(
        self, session_id: str, role: str, content: str, sources: List[Dict] = None
    ):
        """Save a message to the database."""
        db = _SessionLocal()
        try:
            msg = RAGChatMessage(
                session_id=session_id,
                role=role,
                content=content,
                sources=json.dumps(sources or []),
            )
            db.add(msg)
            # Update session last_active
            session = db.query(RAGChatSession).filter(
                RAGChatSession.id == session_id
            ).first()
            if session:
                session.last_active = datetime.utcnow()
            db.commit()
        finally:
            db.close()

    # ------------------------------------------------------------------
    # Document ingestion
    # ------------------------------------------------------------------

    def ingest_documents(
        self,
        session_id: str,
        files: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Ingest documents into a session's vector store.

        Args:
            session_id: Chat session ID
            files: List of dicts with keys: path, filename, content_type

        Returns:
            dict with ingestion stats
        """
        from langchain_core.documents import Document
        from langchain_text_splitters import RecursiveCharacterTextSplitter

        # Load any previously-persisted store so new uploads extend it.
        self._ensure_loaded(session_id)

        all_docs: List[Document] = []
        processed = 0
        errors = []

        for file_info in files:
            file_path = file_info.get("path", "")
            filename = file_info.get("filename", "unknown")
            content_type = file_info.get("content_type", "")

            try:
                loaded = self._load_file(file_path, filename, content_type)
                all_docs.extend(loaded)
                processed += 1
            except Exception as e:
                errors.append(f"{filename}: {str(e)}")

        if not all_docs:
            return {
                "success": False,
                "processed": 0,
                "chunks": 0,
                "errors": errors or ["No documents could be loaded."],
            }

        # Semantic chunking with metadata enrichment
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len,
            separators=["\n\n", "\n", ". ", " ", ""],
        )
        chunks = splitter.split_documents(all_docs)

        # Enrich metadata with a globally-unique chunk id (avoids RRF id
        # collisions across multiple uploads in the same session).
        for i, chunk in enumerate(chunks):
            chunk.metadata["chunk_index"] = i
            chunk.metadata["chunk_id"] = uuid.uuid4().hex
            chunk.metadata["session_id"] = session_id

        # Build / extend FAISS vector store
        embeddings = self._get_embeddings()

        if session_id in self._vector_stores:
            self._vector_stores[session_id].add_documents(chunks)
        else:
            from langchain_community.vectorstores import FAISS

            self._vector_stores[session_id] = FAISS.from_documents(
                chunks, embeddings
            )

        # Build / rebuild BM25 index
        self._rebuild_bm25(session_id, chunks)

        # Persist to disk so the session survives a server restart.
        self._persist(session_id)

        # Update document count in DB
        db = _SessionLocal()
        try:
            session = db.query(RAGChatSession).filter(
                RAGChatSession.id == session_id
            ).first()
            if session:
                session.document_count = (session.document_count or 0) + processed
                session.last_active = datetime.utcnow()
            db.commit()
        finally:
            db.close()

        return {
            "success": True,
            "processed": processed,
            "chunks": len(chunks),
            "errors": errors,
        }

    def _load_file(
        self, file_path: str, filename: str, content_type: str
    ) -> List:
        """Load a file and return LangChain Documents."""
        from langchain_core.documents import Document

        ext = os.path.splitext(filename)[1].lower()

        if ext == ".pdf":
            return self._load_pdf(file_path, filename)
        elif ext == ".docx":
            return self._load_docx(file_path, filename)
        elif ext == ".txt":
            return self._load_txt(file_path, filename)
        else:
            # Try to read as text
            return self._load_txt(file_path, filename)

    @staticmethod
    def _clean_pdf_text(text: str) -> str:
        """Normalize extracted PDF text: de-hyphenate line breaks, collapse
        whitespace, and join wrapped lines into coherent paragraphs."""
        import re

        if not text:
            return ""
        # Join words split across line breaks with a hyphen ("optimi-\nzation").
        text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)
        # Treat blank lines as paragraph breaks; single newlines as soft wraps.
        text = re.sub(r"\n[ \t]*\n", " ", text)  # paragraph sep placeholder
        text = re.sub(r"\n", " ", text)
        text = text.replace(" ", "\n\n")
        # Collapse runs of spaces.
        text = re.sub(r"[ \t]{2,}", " ", text)
        return text.strip()

    def _load_pdf(self, file_path: str, filename: str) -> List:
        """Load PDF using PyMuPDF with reading-order sort + text cleanup."""
        from langchain_core.documents import Document

        try:
            import fitz  # PyMuPDF

            doc = fitz.open(file_path)
            documents = []
            total = len(doc)
            for page_num in range(total):
                page = doc[page_num]
                # sort=True follows visual reading order (helps multi-column papers)
                raw = page.get_text("text", sort=True)
                text = self._clean_pdf_text(raw)
                if text.strip():
                    documents.append(
                        Document(
                            page_content=text,
                            metadata={
                                "source": filename,
                                "page": page_num + 1,
                                "total_pages": total,
                            },
                        )
                    )
            doc.close()
            return documents
        except ImportError:
            # Fallback to PyPDF2
            from PyPDF2 import PdfReader

            reader = PdfReader(file_path)
            documents = []
            for i, page in enumerate(reader.pages):
                text = self._clean_pdf_text(page.extract_text() or "")
                if text.strip():
                    documents.append(
                        Document(
                            page_content=text,
                            metadata={
                                "source": filename,
                                "page": i + 1,
                                "total_pages": len(reader.pages),
                            },
                        )
                    )
            return documents

    def _load_docx(self, file_path: str, filename: str) -> List:
        """Load DOCX file."""
        from langchain_core.documents import Document

        try:
            import docx

            doc = docx.Document(file_path)
            text = "\n".join(p.text for p in doc.paragraphs if p.text.strip())
            if text.strip():
                return [
                    Document(
                        page_content=text,
                        metadata={"source": filename, "format": "docx"},
                    )
                ]
        except Exception as e:
            raise RuntimeError(f"Failed to load DOCX: {e}")
        return []

    def _load_txt(self, file_path: str, filename: str) -> List:
        """Load plain text file."""
        from langchain_core.documents import Document

        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            text = f.read()
        if text.strip():
            return [
                Document(
                    page_content=text,
                    metadata={"source": filename, "format": "txt"},
                )
            ]
        return []

    # ------------------------------------------------------------------
    # BM25 index
    # ------------------------------------------------------------------

    def _rebuild_bm25(self, session_id: str, new_chunks: List):
        """Rebuild BM25 index with existing + new chunks."""
        from rank_bm25 import BM25Okapi

        existing = self._bm25_data.get(session_id, {}).get("corpus_docs", [])
        all_docs = existing + new_chunks

        # Tokenize for BM25
        tokenized = [doc.page_content.lower().split() for doc in all_docs]

        if tokenized:
            bm25 = BM25Okapi(tokenized)
            self._bm25_data[session_id] = {
                "corpus_docs": all_docs,
                "bm25": bm25,
            }

    # ------------------------------------------------------------------
    # Hybrid retrieval
    # ------------------------------------------------------------------

    def _retrieve_hybrid(
        self, session_id: str, query: str, k: int = 6
    ) -> List[Dict[str, Any]]:
        """
        Hybrid retrieval combining FAISS vector search + BM25 keyword search
        with Reciprocal Rank Fusion (RRF).
        """
        self._ensure_loaded(session_id)
        results = []

        # --- FAISS vector search ---
        vector_results = []
        if session_id in self._vector_stores:
            try:
                vector_results = self._vector_stores[
                    session_id
                ].similarity_search_with_score(query, k=k * 2)
            except Exception:
                pass

        # --- BM25 keyword search ---
        bm25_results = []
        if session_id in self._bm25_data:
            bm25_info = self._bm25_data[session_id]
            bm25 = bm25_info.get("bm25")
            corpus_docs = bm25_info.get("corpus_docs", [])
            if bm25 and corpus_docs:
                try:
                    tokenized_query = query.lower().split()
                    scores = bm25.get_scores(tokenized_query)
                    # Get top-k indices
                    top_indices = sorted(
                        range(len(scores)),
                        key=lambda i: scores[i],
                        reverse=True,
                    )[: k * 2]
                    bm25_results = [
                        (corpus_docs[i], scores[i]) for i in top_indices if scores[i] > 0
                    ]
                except Exception:
                    pass

        # --- Reciprocal Rank Fusion ---
        rrf_constant = 60  # Standard RRF constant
        doc_scores: Dict[str, float] = {}
        doc_map: Dict[str, Any] = {}

        # Add vector results with RRF scores
        for rank, (doc, score) in enumerate(vector_results):
            doc_id = doc.metadata.get("chunk_id") or f"{doc.metadata.get('source', '')}_{doc.metadata.get('chunk_index', rank)}"
            rrf_score = 1.0 / (rrf_constant + rank + 1)
            doc_scores[doc_id] = doc_scores.get(doc_id, 0) + rrf_score
            doc_map[doc_id] = doc

        # Add BM25 results with RRF scores
        for rank, (doc, score) in enumerate(bm25_results):
            doc_id = doc.metadata.get("chunk_id") or f"{doc.metadata.get('source', '')}_{doc.metadata.get('chunk_index', rank)}"
            rrf_score = 1.0 / (rrf_constant + rank + 1)
            doc_scores[doc_id] = doc_scores.get(doc_id, 0) + rrf_score
            if doc_id not in doc_map:
                doc_map[doc_id] = doc

        # Sort by fused score and return top-k
        sorted_ids = sorted(
            doc_scores.keys(), key=lambda x: doc_scores[x], reverse=True
        )[:k]

        for doc_id in sorted_ids:
            doc = doc_map[doc_id]
            results.append(
                {
                    "content": doc.page_content,
                    "source": doc.metadata.get("source", "unknown"),
                    "page": doc.metadata.get("page", None),
                    "score": round(doc_scores[doc_id], 4),
                }
            )

        return results

    # ------------------------------------------------------------------
    # Conversational QA
    # ------------------------------------------------------------------

    def query(
        self, session_id: str, question: str
    ) -> Dict[str, Any]:
        """
        Answer a question using hybrid retrieval + conversation history.

        Returns dict with keys: answer, sources
        """
        # Load the persisted store if it isn't in memory (e.g. after restart).
        if not self._ensure_loaded(session_id):
            return {
                "answer": "Please upload documents first before asking questions.",
                "sources": [],
            }

        # Get conversation history (last 6 messages for context)
        history = self.get_messages(session_id)
        recent_history = history[-6:] if len(history) > 6 else history

        # Expand short / follow-up questions into a standalone retrieval query.
        retrieval_query = self._contextualize_query(question, recent_history)

        # Retrieve relevant chunks
        retrieved = self._retrieve_hybrid(session_id, retrieval_query, k=6)

        if not retrieved:
            answer = self._chat(
                f"The user asked: {question}\n\n"
                "No relevant documents were found. Please let the user know "
                "and suggest they upload relevant documents.",
                max_tokens=500,
            )
            self._save_message(session_id, "user", question)
            self._save_message(session_id, "assistant", answer, [])
            return {"answer": answer, "sources": []}

        # Build context from retrieved chunks
        context_parts = []
        for i, chunk in enumerate(retrieved, 1):
            source_info = f"[Source: {chunk['source']}"
            if chunk.get("page"):
                source_info += f", Page {chunk['page']}"
            source_info += "]"
            context_parts.append(f"--- Chunk {i} {source_info} ---\n{chunk['content']}")
        context = "\n\n".join(context_parts)

        # Build conversation history string
        history_str = ""
        if recent_history:
            history_lines = []
            for msg in recent_history:
                role = "User" if msg["role"] == "user" else "Assistant"
                # Truncate long messages in history
                content = msg["content"][:500]
                history_lines.append(f"{role}: {content}")
            history_str = "\n".join(history_lines)

        # Generate answer with comprehensive prompt
        prompt = f"""You are a highly knowledgeable research assistant analyzing uploaded documents.
Your goal is to provide accurate, well-structured, and contextual answers based ONLY on the
provided document context. If the answer cannot be found in the context, say so clearly.

RULES:
1. Base your answer strictly on the provided context
2. Cite sources by mentioning the document name and page number when available
3. If the context is insufficient, acknowledge what you do know and what's missing
4. Use clear, academic language
5. Structure long answers with bullet points or numbered lists when appropriate
6. Consider the conversation history for context continuity

{"CONVERSATION HISTORY:" + chr(10) + history_str if history_str else ""}

RETRIEVED DOCUMENT CONTEXT:
{context}

USER QUESTION: {question}

Provide a comprehensive, well-structured answer:"""

        answer = self._chat(prompt, max_tokens=1500, temperature=0.2)

        # Prepare source references
        sources = [
            {
                "source": chunk["source"],
                "page": chunk.get("page"),
                "relevance": chunk["score"],
                "snippet": chunk["content"][:200] + "..."
                if len(chunk["content"]) > 200
                else chunk["content"],
            }
            for chunk in retrieved[:4]  # Top 4 sources
        ]

        # Save messages
        self._save_message(session_id, "user", question)
        self._save_message(session_id, "assistant", answer, sources)

        return {
            "answer": answer,
            "sources": sources,
        }

    # ------------------------------------------------------------------
    # Check if session has documents
    # ------------------------------------------------------------------

    def session_has_documents(self, session_id: str) -> bool:
        """Check if a session has ingested documents (in memory or on disk)."""
        if session_id in self._vector_stores:
            return True
        return (self._store_path(session_id) / "faiss").exists()
