# Doc Chat Feature

## What does it do?

Doc Chat is a retrieval-augmented conversational interface for working with uploaded documents. It allows a user to build a private, session-scoped knowledge space from PDFs, DOCX files, and plain text, then ask natural language questions and receive answers grounded in the uploaded sources. The feature is designed for research workflows where the user must navigate long or heterogeneous documents and needs traceable answers rather than generic summaries. Each chat session preserves its own message history, enabling multi-turn investigation of the same corpus without losing context across questions.

In practice, Doc Chat behaves like a domain-specific assistant: it retrieves relevant passages from the user’s documents, blends them with the ongoing conversation, and generates responses that reference the original source material. This improves trust and auditability for academic or professional use cases, where the user must verify claims and cite sources accurately.

## How does it work?

The pipeline has two phases: ingestion and query.

Ingestion phase:

1. Session creation: a session is created and stored in persistent storage to isolate conversations and document collections.
2. File intake: the user uploads one or more files. Each file is validated for type and size before ingestion to prevent unsupported formats from entering the pipeline.
3. Parsing and chunking: documents are parsed into plain text and then split into overlapping chunks suitable for retrieval. Chunking preserves local context while keeping each segment small enough for embedding and indexing.
4. Index construction: embeddings are computed for each chunk and stored in a FAISS index for vector similarity search. In parallel, a lexical index (BM25) is built to support keyword-based retrieval. The combination forms a hybrid retriever that balances semantic matching with exact term coverage.

Query phase:

1. Context retrieval: when a question is asked, the hybrid retriever scores candidate chunks from the session’s indexed documents. Both semantic similarity and lexical overlap influence the final selection.
2. Conversation blending: the highest scoring chunks are combined with the current session history to preserve conversational continuity, reducing the risk of disconnected answers.
3. LLM response: the LLM receives the question, the conversation history, and the retrieved context, and generates a response that is constrained to the available sources.
4. Source attribution: the system returns source snippets alongside the answer, allowing the user to verify evidence and trace statements back to the original documents.

This two-stage design ensures that the assistant is grounded in user-provided data rather than general training knowledge, which is critical for trustworthy document analysis.

## Technologies used

- Next.js page: web/src/app/doc-chat/page.tsx
- Backend RAG engine: backend/core_agents/rag_agent.py
- SQLAlchemy and SQLite session persistence
- FAISS for vector retrieval and BM25 for lexical retrieval

## Inputs and outputs

Inputs:

- Session name (used to scope storage and history)
- Uploaded files (PDF, DOCX, TXT)
- Natural language questions

Outputs:

- Assistant answers grounded in retrieved context
- Source references/snippets to support auditability
- Persisted multi-turn history for continued investigation

## API dependencies

- /api/rag/sessions (create/list/delete)
- /api/rag/upload
- /api/rag/query
- /api/rag/messages/{session_id}

## Failure modes and guardrails

Unsupported file types are blocked at upload time, which prevents parsing errors from entering downstream stages. Queries require an existing session, ensuring that the system always has a scope for retrieval. If the retriever returns weak or empty context, the system provides fallback responses rather than fabricating details. Including source snippets in every response improves transparency and makes it easier to detect and correct model errors.

## Performance and scaling notes

Ingestion cost scales with both file size and file count, as larger corpora require more chunking and embedding computation. Query latency depends on retrieval depth, index size, and LLM response time. Hybrid retrieval is more accurate than single-mode retrieval but introduces additional scoring overhead; this trade-off is acceptable for document-centric research workflows where correctness is prioritized.

## Extension ideas

- Add citation-ready answer formatting that outputs references in IEEE or APA style.
- Add per-message confidence scores and retrieval diagnostics to help users judge answer reliability.
