from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from typing import Any, Dict, List
import os
import json
import re
import importlib
from io import BytesIO

from PyPDF2 import PdfReader

from backend.api.config import get_settings

try:
    from groq import Groq
except Exception:
    Groq = None

try:
    from google import genai
except Exception:
    genai = None

try:
    from core_agents.llm_provider import chat_completion as _llm_chat
except Exception:
    _llm_chat = None  # type: ignore[assignment]

from core_agents.query_agent import ScientificQueryAgent
from core_agents.keyword_agent import KeywordExtractionAgent
from core_agents.retrieval_agent import PaperRetrievalAgent
from core_agents.summarization_agent import PaperSummarizationAgent
from core_agents.plagiarism_agent import PlagiarismDetectionAgent
from core_agents.citation_agent import CitationAgent
from core_agents.diagram_agent import DiagramAgent
from core_agents.pseudocode_agent import PseudocodeAgent
from core_agents.github_paper_agent import GitHubPaperAgent
from core_agents.rag_agent import RAGAgent
from fine_tuning.fine_tuned_drafting_agent import get_drafting_agent, DraftingConfig

from api.schemas import (
    QueryRequest,
    RetrieveRequest,
    SummarizeRequest,
    DraftRequest,
    PlagiarismRequest,
    CitationRequest,
    RefineBlockRequest,
    AutocompleteRequest,
    AutocompleteResponse,
    DiagramRequest,
    PseudocodeRequest,
    CitationSuggestRequest,
    CitationFormatRequest,
    CitationSuggestResponse,
    FormatCommandRequest,
    FormatIEEERequest,
    CompilePDFRequest,
    ExtractTextResponse,
    GitHubToIEEERequest,
    GitHubToIEEEResponse,
    KeywordExtractRequest,
    KeywordExtractResponse,
    RAGQueryRequest,
    RAGQueryResponse,
    RAGSessionResponse,
    RAGSessionListItem,
    RAGMessageResponse,
    RAGUploadResponse,
)

settings = get_settings()

app = FastAPI(title=settings.api_title, version=settings.api_version)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

query_agent = ScientificQueryAgent()
keyword_agent = KeywordExtractionAgent()
retrieval_agent = PaperRetrievalAgent(keyword_agent=keyword_agent)
summarization_agent = PaperSummarizationAgent()
plagiarism_agent = PlagiarismDetectionAgent()
citation_agent = CitationAgent()
diagram_agent = DiagramAgent()
pseudocode_agent = PseudocodeAgent()
github_paper_agent = GitHubPaperAgent()
rag_agent = RAGAgent()


def _refine_with_groq(prompt: str) -> str | None:
    api_key = os.getenv("GROQ_API_KEY", "").strip()
    if not api_key or Groq is None:
        return None
    try:
        client = Groq(api_key=api_key)
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            top_p=0.9,
            max_tokens=400,
        )
        return response.choices[0].message.content.strip()
    except Exception:
        return None


def _refine_with_gemini(prompt: str) -> str | None:
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key or genai is None:
        return None
    try:
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config={
                "temperature": 0.3,
                "top_p": 0.9,
                "max_output_tokens": 400,
            },
        )
        return response.text.strip() if response and response.text else None
    except Exception:
        return None


def _refine_with_any(prompt: str) -> str | None:
    """Try Ollama -> Groq -> Gemini for text refinement."""
    if _llm_chat is not None:
        result = _llm_chat(prompt, max_tokens=400, temperature=0.3, top_p=0.9)
        if result:
            return result
    result = _refine_with_groq(prompt)
    if result:
        return result
    return _refine_with_gemini(prompt)


def _autocomplete_with_groq(text: str, max_suggestions: int = 3) -> List[str] | None:
    api_key = os.getenv("GROQ_API_KEY", "").strip()
    if not api_key or Groq is None:
        return None
    prompt = (
        "You are an academic writing autocomplete engine. "
        "Return ONLY valid JSON object with key suggestions as a list of short continuation phrases. "
        f"Provide at most {max_suggestions} suggestions, no numbering, no markdown.\n\n"
        f"Context:\n{text[-1200:]}"
    )
    try:
        client = Groq(api_key=api_key)
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.4,
            top_p=0.9,
            max_tokens=160,
        )
        content = response.choices[0].message.content.strip()
        data = _parse_json_block(content)
        if not data:
            return None
        suggestions = data.get("suggestions", [])
        if not isinstance(suggestions, list):
            return None
        return [str(s).strip() for s in suggestions if str(s).strip()][:max_suggestions]
    except Exception:
        return None


def _max_ngram_overlap(text: str, source_texts: List[str], n: int = 6) -> float:
    words = re.findall(r"\w+", text.lower())
    if len(words) < n:
        return 0.0
    text_ngrams = {tuple(words[i:i + n]) for i in range(0, len(words) - n + 1)}
    if not text_ngrams:
        return 0.0
    max_overlap = 0.0
    for src in source_texts:
        src_words = re.findall(r"\w+", (src or "").lower())
        if len(src_words) < n:
            continue
        src_ngrams = {tuple(src_words[i:i + n]) for i in range(0, len(src_words) - n + 1)}
        if not src_ngrams:
            continue
        overlap = len(text_ngrams.intersection(src_ngrams)) / max(len(text_ngrams), 1)
        if overlap > max_overlap:
            max_overlap = overlap
    return round(max_overlap, 4)


def _parse_json_block(text: str) -> Dict[str, Any] | None:
    try:
        return json.loads(text)
    except Exception:
        match = re.search(r"\{[\s\S]*\}", text)
        if not match:
            return None
        try:
            return json.loads(match.group(0))
        except Exception:
            return None


def _format_with_groq(prompt: str) -> Dict[str, Any] | None:
    api_key = os.getenv("GROQ_API_KEY", "").strip()
    if not api_key or Groq is None:
        return None
    try:
        client = Groq(api_key=api_key)
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            top_p=0.1,
            max_tokens=300,
        )
        content = response.choices[0].message.content.strip()
        return _parse_json_block(content)
    except Exception:
        return None


def _format_with_any(prompt: str) -> Dict[str, Any] | None:
    """Try Ollama -> Groq for JSON format commands."""
    if _llm_chat is not None:
        raw = _llm_chat(prompt, max_tokens=300, temperature=0.0, top_p=0.1)
        if raw:
            data = _parse_json_block(raw)
            if data:
                return data
    return _format_with_groq(prompt)


def _autocomplete_with_groq(text: str, max_suggestions: int = 3) -> List[str] | None:
    api_key = os.getenv("GROQ_API_KEY", "").strip()
    if not api_key or Groq is None:
        return None
    prompt = (
        "You are an academic writing autocomplete engine. "
        "Return ONLY valid JSON object with key suggestions as a list of short continuation phrases. "
        f"Provide at most {max_suggestions} suggestions, no numbering, no markdown.\n\n"
        f"Context:\n{text[-1200:]}"
    )
    try:
        client = Groq(api_key=api_key)
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.4,
            top_p=0.9,
            max_tokens=160,
        )
        content = response.choices[0].message.content.strip()
        data = _parse_json_block(content)
        if not data:
            return None
        suggestions = data.get("suggestions", [])
        if not isinstance(suggestions, list):
            return None
        return [str(s).strip() for s in suggestions if str(s).strip()][:max_suggestions]
    except Exception:
        return None


def _autocomplete_with_any(text: str, max_suggestions: int = 3) -> List[str] | None:
    """Try Ollama -> Groq for autocomplete (returns parsed suggestions list)."""
    prompt = (
        "You are an academic writing autocomplete engine. "
        "Return ONLY valid JSON object with key suggestions as a list of short continuation phrases. "
        f"Provide at most {max_suggestions} suggestions, no numbering, no markdown.\n\n"
        f"Context:\n{text[-1200:]}"
    )
    # Ollama
    if _llm_chat is not None:
        raw = _llm_chat(prompt, max_tokens=160, temperature=0.4, top_p=0.9)
        if raw:
            data = _parse_json_block(raw)
            if data:
                suggestions = data.get("suggestions", [])
                if isinstance(suggestions, list):
                    result = [str(s).strip() for s in suggestions if str(s).strip()][:max_suggestions]
                    if result:
                        return result
    # Groq fallback
    return _autocomplete_with_groq(text, max_suggestions)


def _max_ngram_overlap(text: str, source_texts: List[str], n: int = 6) -> float:
    words = re.findall(r"\w+", text.lower())
    if len(words) < n:
        return 0.0
    text_ngrams = {tuple(words[i:i + n]) for i in range(0, len(words) - n + 1)}
    if not text_ngrams:
        return 0.0
    max_overlap = 0.0
    for src in source_texts:
        src_words = re.findall(r"\w+", (src or "").lower())
        if len(src_words) < n:
            continue
        src_ngrams = {tuple(src_words[i:i + n]) for i in range(0, len(src_words) - n + 1)}
        if not src_ngrams:
            continue
        overlap = len(text_ngrams.intersection(src_ngrams)) / max(len(text_ngrams), 1)
        if overlap > max_overlap:
            max_overlap = overlap
    return round(max_overlap, 4)


def _parse_json_block(text: str) -> Dict[str, Any] | None:
    try:
        return json.loads(text)
    except Exception:
        match = re.search(r"\{[\s\S]*\}", text)
        if not match:
            return None
        try:
            return json.loads(match.group(0))
        except Exception:
            return None


def _format_with_groq(prompt: str) -> Dict[str, Any] | None:
    api_key = os.getenv("GROQ_API_KEY", "").strip()
    if not api_key or Groq is None:
        return None
    try:
        client = Groq(api_key=api_key)
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            top_p=0.1,
            max_tokens=300,
        )
        content = response.choices[0].message.content.strip()
        return _parse_json_block(content)
    except Exception:
        return None


def _format_with_any(prompt: str) -> Dict[str, Any] | None:
    """Try Ollama -> Groq for JSON format commands."""
    if _llm_chat is not None:
        raw = _llm_chat(prompt, max_tokens=300, temperature=0.0, top_p=0.1)
        if raw:
            data = _parse_json_block(raw)
            if data:
                return data
    return _format_with_groq(prompt)


@app.get("/api/health")
def health() -> Dict[str, Any]:
    return {"status": "ok"}


@app.post("/api/extract-text")
async def extract_text(file: UploadFile = File(...)) -> ExtractTextResponse:
    try:
        filename = file.filename or "uploaded_file"
        extension = os.path.splitext(filename)[1].lower()
        content = await file.read()

        if not content:
            raise HTTPException(status_code=400, detail="Uploaded file is empty")

        if len(content) > 15 * 1024 * 1024:
            raise HTTPException(status_code=413, detail="File too large (max 15MB)")

        warnings: List[str] = []
        text = ""

        if extension == ".txt":
            text = content.decode("utf-8", errors="ignore")
        elif extension == ".pdf":
            reader = PdfReader(BytesIO(content))
            parts: List[str] = []
            for page in reader.pages:
                try:
                    parts.append(page.extract_text() or "")
                except Exception:
                    parts.append("")
            text = "\n".join(parts).strip()
        elif extension == ".docx":
            try:
                docx_module = importlib.import_module("docx")
                document_cls = getattr(docx_module, "Document")
            except Exception:
                raise HTTPException(
                    status_code=500,
                    detail="DOCX parsing not available. Install python-docx.",
                )
            doc = document_cls(BytesIO(content))
            chunks: List[str] = []

            for paragraph in doc.paragraphs:
                if paragraph.text and paragraph.text.strip():
                    chunks.append(paragraph.text.strip())

            for table in doc.tables:
                for row in table.rows:
                    row_cells = [cell.text.strip() for cell in row.cells if cell.text.strip()]
                    if row_cells:
                        chunks.append(" | ".join(row_cells))

            for section in doc.sections:
                for paragraph in section.header.paragraphs:
                    if paragraph.text and paragraph.text.strip():
                        chunks.append(paragraph.text.strip())
                for paragraph in section.footer.paragraphs:
                    if paragraph.text and paragraph.text.strip():
                        chunks.append(paragraph.text.strip())

            text = "\n".join(chunks).strip()
        elif extension == ".doc":
            warnings.append(
                "Legacy .doc parsing is not supported yet. Please convert to .docx for best results."
            )
        else:
            raise HTTPException(
                status_code=400,
                detail="Unsupported file type. Allowed: .txt, .pdf, .docx, .doc",
            )

        if not text:
            warnings.append(
                "No extractable text detected. If this is a scanned document/image PDF, OCR is required."
            )

        return ExtractTextResponse(
            success=True,
            text=text,
            filename=filename,
            extension=extension,
            warnings=warnings,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/query")
def analyze_topic(req: QueryRequest) -> Dict[str, Any]:
    try:
        return query_agent.run(req.text, top_keywords=req.top_keywords)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/keywords/extract", response_model=KeywordExtractResponse)
def extract_keywords(req: KeywordExtractRequest) -> KeywordExtractResponse:
    """Extract scientific keywords from text with optional LLM enrichment."""
    try:
        result = keyword_agent.extract(
            text=req.text,
            top_n=req.top_n,
            use_llm=req.use_llm,
            expand_acronyms=req.expand_acronyms,
            return_synonyms=req.return_synonyms,
        )
        keywords = [
            {"text": k.get("text", ""), "score": k.get("score", 0.0), "type": k.get("type", "core")}
            for k in result.get("keywords", [])
        ]
        return KeywordExtractResponse(
            keywords=keywords,
            synonyms=result.get("synonyms") or {},
            provider=result.get("provider", "fallback"),
            elapsed_ms=result.get("elapsed_ms", 0),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/retrieve")
def retrieve_papers(req: RetrieveRequest) -> Dict[str, Any]:
    try:
        if req.use_multi_query and req.subtopics:
            return retrieval_agent.retrieve_papers_multi_query(
                req.keywords, req.subtopics, max_results=req.max_results, domain=req.domain
            )
        return retrieval_agent.retrieve_papers(
            req.keywords,
            max_results=req.max_results,
            sources=req.sources,
            domain=req.domain,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/summarize")
def summarize(req: SummarizeRequest) -> Dict[str, Any]:
    try:
        return summarization_agent.generate_comprehensive_summary(req.papers, req.keywords)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/draft")
def draft(req: DraftRequest) -> Dict[str, str]:
    try:
        config = DraftingConfig()
        if req.config:
            config.max_new_tokens = req.config.max_new_tokens
            config.min_new_tokens = req.config.min_new_tokens
            config.temperature = req.config.temperature
            config.top_p = req.config.top_p
            config.repetition_penalty = req.config.repetition_penalty
            config.num_beams = req.config.num_beams
            config.no_repeat_ngram_size = req.config.no_repeat_ngram_size

        drafting_agent = get_drafting_agent(config)
        return drafting_agent.generate_complete_draft(
            req.research_topic, req.comprehensive_summary, req.keywords
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/plagiarism")
def plagiarism(req: PlagiarismRequest) -> Dict[str, Any]:
    try:
        return plagiarism_agent.check_plagiarism(
            req.generated_draft, req.source_papers, req.research_topic
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def _extract_keywords_from_claim(claim_text: str, max_keywords: int = 8) -> List[str]:
    """Use KeywordExtractionAgent for consistent, high-quality keyword extraction."""
    try:
        result = keyword_agent.extract(
            claim_text,
            top_n=max_keywords,
            use_llm=True,
            expand_acronyms=True,
            return_synonyms=False,
        )
        keywords = result.get("keywords", [])
        return [k["text"] for k in keywords if k.get("text")]
    except Exception as exc:
        print(f"   [!] Keyword agent extraction failed in claim helper: {exc}")
        # Fallback to simple regex extraction
        words = re.findall(r"[a-zA-Z][a-zA-Z-]{2,}", claim_text.lower())
        stopwords = {
            "the", "and", "for", "with", "that", "this", "from", "into", "were", "was",
            "are", "have", "has", "had", "will", "would", "could", "should", "about", "their",
            "there", "which", "while", "where", "when", "than", "then", "also", "using", "used",
            "use", "over", "under", "between", "among", "research", "study", "studies", "paper",
            "find", "shows", "show", "found", "suggest", "suggests", "indicate", "indicates",
        }
        counts: Dict[str, int] = {}
        for word in words:
            if word in stopwords:
                continue
            counts[word] = counts.get(word, 0) + 1
        return [w for w, _ in sorted(counts.items(), key=lambda item: item[1], reverse=True)[:max_keywords]]


@app.post("/api/citation/suggest", response_model=CitationSuggestResponse)
def suggest_citation(req: CitationSuggestRequest) -> CitationSuggestResponse:
    try:
        claim_text = req.claim_text.strip()
        if not claim_text:
            raise HTTPException(status_code=400, detail="claim_text is required")

        citation_style = req.citation_style.lower().strip() or "apa"
        if citation_style not in {"apa", "ieee", "mla"}:
            citation_style = "apa"

        papers: List[Dict[str, Any]] = list(req.provided_papers)
        notes: List[str] = []

        if not papers and req.auto_retrieve:
            keywords = req.keywords or _extract_keywords_from_claim(
                f"{claim_text} {req.context_text}".strip(),
                max_keywords=8,
            )
            if keywords:
                result = retrieval_agent.retrieve_papers(
                    keywords,
                    max_results=req.retrieve_max_results,
                )
                papers = result.get("papers", [])
            else:
                notes.append("No usable keywords found for retrieval.")

        if not papers:
            return CitationSuggestResponse(
                success=True,
                claim_text=claim_text,
                citation_style=citation_style,
                candidates=[],
                confidence=0.0,
                source_count=0,
                notes=notes + ["No source papers available for citation suggestion."],
            )

        ranked = citation_agent.find_relevant_citations(claim_text, papers)
        ranked = ranked[: req.max_candidates]

        if not ranked:
            fallback_ranked = sorted(
                papers,
                key=lambda p: float(p.get("relevance_score", 0.0)),
                reverse=True,
            )[: req.max_candidates]
            ranked = [
                {
                    "paper": p,
                    "relevance_score": float(p.get("relevance_score", 0.0)),
                    "citation_type": "general",
                }
                for p in fallback_ranked
            ]
            if ranked:
                notes.append(
                    "Strict claim matching found no strong hit; returning best retrieved sources."
                )

        candidates = []
        for idx, item in enumerate(ranked, start=1):
            paper = item.get("paper", {})
            formatted = citation_agent.format_citation(
                paper,
                citation_style=citation_style,
                citation_number=idx,
            )
            paper_info = formatted.get("paper_info", {})
            doi_or_url = paper.get("doi") or paper.get("pdf_url") or paper.get("entry_id") or ""

            candidates.append(
                {
                    "title": paper_info.get("title", ""),
                    "authors": paper_info.get("authors", ""),
                    "year": paper_info.get("year", ""),
                    "source": paper_info.get("source", ""),
                    "doi_or_url": doi_or_url,
                    "relevance_score": float(item.get("relevance_score", 0.0)),
                    "citation_type": item.get("citation_type", "general"),
                    "in_text": formatted.get("in_text", ""),
                    "reference": formatted.get("reference", ""),
                }
            )

        confidence = max((c["relevance_score"] for c in candidates), default=0.0)
        if confidence < 0.45:
            notes.append("Low confidence citation suggestions; manual verification recommended.")

        return CitationSuggestResponse(
            success=True,
            claim_text=claim_text,
            citation_style=citation_style,
            candidates=candidates,
            confidence=confidence,
            source_count=len(papers),
            notes=notes,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/citation/format")
def format_citation(req: CitationFormatRequest) -> Dict[str, Any]:
    try:
        citation_style = req.citation_style.lower().strip() or "apa"
        if citation_style not in {"apa", "ieee", "mla"}:
            citation_style = "apa"
        return citation_agent.format_citation(
            req.paper,
            citation_style=citation_style,
            citation_number=req.citation_number,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/autocomplete", response_model=AutocompleteResponse)
def autocomplete(req: AutocompleteRequest) -> AutocompleteResponse:
    try:
        text = (req.text or "").strip()
        if not text:
            return AutocompleteResponse(
                suggestions=[
                    "This study demonstrates that",
                    "The results indicate that",
                    "A key contribution is",
                ][: req.max_suggestions],
                provider="fallback",
            )

        suggestions = _autocomplete_with_any(text, req.max_suggestions)
        provider = "ollama/groq"

        if not suggestions:
            tail = " ".join(text.lower().split()[-4:])
            base = [
                "This study demonstrates that",
                "The results indicate that",
                "A key contribution is",
                "These findings suggest that",
                "Future work should",
            ]
            if "method" in tail or "approach" in tail:
                base = [
                    "The proposed method improves",
                    "This approach achieves",
                    "Empirical evaluation shows",
                ]
            suggestions = base[: req.max_suggestions]
            provider = "fallback"

        return AutocompleteResponse(suggestions=suggestions, provider=provider)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/refine-block")
def refine_block(req: RefineBlockRequest) -> Dict[str, Any]:
    try:
        mode = req.mode.lower().strip()
        instruction = {
            "expand": "Expand the text into a well-structured paragraph.",
            "academic": "Rewrite the text in formal academic tone.",
            "refine": "Refine clarity and flow without changing meaning.",
            "anti_plagiarism": (
                "Rewrite in formal academic tone while substantially changing wording and sentence structure "
                "to minimize phrase overlap. Keep the meaning unchanged."
            ),
        }.get(mode, "Refine clarity and flow without changing meaning.")

        prompt = (
            "You are an academic writing assistant. Do not add new facts. "
            f"{instruction}\n\nText:\n{req.text}"
        )

        output = _refine_with_any(prompt)
        provider = "ollama/groq/gemini"

        if not output:
            output = req.text.strip()
            provider = "fallback"

        warnings: List[str] = []
        overlap_score = 0.0
        if req.source_texts:
            overlap_score = _max_ngram_overlap(output, req.source_texts, n=6)
            if overlap_score >= 0.18:
                warnings.append("High lexical overlap detected; applying stronger paraphrase.")
                strengthen_prompt = (
                    "Rewrite again with lower lexical overlap. Use different sentence structure and synonym substitutions. "
                    "Do not change factual meaning. Return only rewritten text.\n\n"
                    f"Text:\n{output}"
                )
                stronger = _refine_with_any(strengthen_prompt)
                if stronger:
                    output = stronger
                    overlap_score = _max_ngram_overlap(output, req.source_texts, n=6)

        return {
            "refined_text": output,
            "provider": provider,
            "overlap_score": overlap_score,
            "warnings": warnings,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/diagram")
def generate_diagram(req: DiagramRequest) -> Dict[str, Any]:
    try:
        return diagram_agent.generate_diagram(req.description, req.diagram_type)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/pseudocode")
def convert_to_pseudocode(req: PseudocodeRequest) -> Dict[str, Any]:
    try:
        return pseudocode_agent.convert_to_pseudocode(req.code, req.algorithm_name)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/format-commands")
def format_commands(req: FormatCommandRequest) -> Dict[str, Any]:
    try:
        prompt = (
            "You are a layout assistant for academic papers. "
            "Return ONLY strict JSON with this schema: "
            "{\"cssUpdates\": {\"--col-count\": 1}, "
            "\"editorCommands\": [{\"target\": \"abstract\", \"action\": \"toggleBold\"}]}. "
            "Rules: output JSON only, no markdown. "
            "Allowed css keys: --col-count, --col-gap, --font-size, --margin-x, --margin-y. "
            "Allowed editor actions: toggleBold, toggleItalic, toggleHeading1, toggleHeading2. "
            f"Current settings: {req.settings}. "
            f"Available targets: {req.available_targets}. "
            f"User request: {req.prompt}"
        )

        data = _format_with_any(prompt)
        if not data:
            return {"cssUpdates": {}, "editorCommands": [], "provider": "fallback"}

        css_updates = data.get("cssUpdates", {}) if isinstance(data, dict) else {}
        editor_cmds = data.get("editorCommands", []) if isinstance(data, dict) else []
        if not isinstance(css_updates, dict):
            css_updates = {}
        if not isinstance(editor_cmds, list):
            editor_cmds = []

        normalized_cmds = []
        for cmd in editor_cmds:
            if not isinstance(cmd, dict):
                continue
            target = str(cmd.get("target", "")).strip()
            action = str(cmd.get("action", "")).strip()
            if not target or not action:
                continue
            normalized_cmds.append({"target": target, "action": action})

        return {
            "cssUpdates": css_updates,
            "editorCommands": normalized_cmds,
            "provider": "groq",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def _format_ieee_with_ai(raw_text: str, format_type: str) -> Dict[str, Any] | None:
    """Use AI to structure raw text into IEEE format HTML. Tries Ollama -> Groq."""
    prompt = f"""You are an IEEE research paper formatting expert. Convert the following raw text into well-structured HTML for an IEEE {format_type} paper.

CRITICAL RULES:
0. First pass: fix grammar, punctuation, capitalization, and sentence flow while preserving technical meaning.
1. Detect and structure sections: Title, Abstract, Introduction, Methodology, Results, Discussion, Conclusion, References
2. Use this HTML structure:
   - Title: <h1>TITLE HERE</h1>
   - Section headers (I. INTRODUCTION): <h1>I. INTRODUCTION</h1>
   - Subsection headers (A. Background): <h2>A. Background</h2>
   - Paragraphs: <p>text</p>
   - Bold: <strong>text</strong>
   - Italic: <em>text</em>
   - Lists: <ul><li>item</li></ul> or <ol><li>item</li></ol>

3. TABLES - VERY IMPORTANT: Convert ASCII tables or tabular data into proper HTML tables:
   <table>
     <thead><tr><th>Header1</th><th>Header2</th></tr></thead>
     <tbody><tr><td>Data1</td><td>Data2</td></tr></tbody>
   </table>
     - If a table is malformed (inconsistent delimiters/column counts), normalize it:
         - infer separators (|, tabs, commas, multiple spaces)
         - infer header row when present
         - ensure each row has the same number of columns (pad missing cells with empty strings)
         - remove decorative ASCII border rows

4. EQUATIONS - Convert LaTeX/math notation:
   - Inline math like $x^2$ becomes: <em>x²</em>
   - Block equations become: <blockquote><em>Equation: content</em></blockquote>
   - Greek letters: $\\alpha$ → α, $\\beta$ → β, $\\delta$ → δ, $\\lambda$ → λ
   - Subscripts: $x_i$ → x<sub>i</sub>
   - Superscripts: $x^2$ → x<sup>2</sup>

5. For references, format as: <p>[1] Author, "Title," Journal, year.</p>
6. Use Roman numerals (I, II, III) for main sections
7. Use letters (A, B, C) for subsections  
8. Make the abstract content italic with <em>
9. Return ONLY the HTML content, no explanations or markdown code blocks

RAW TEXT:
{raw_text[:12000]}

Return the formatted HTML:"""

    def _parse_html_response(html_content: str) -> Dict[str, Any]:
        if html_content.startswith("```"):
            html_content = re.sub(r'^```\w*\n?', '', html_content)
            html_content = re.sub(r'\n?```$', '', html_content)
        sections = len(re.findall(r'<h1>', html_content, re.IGNORECASE))
        equations = len(re.findall(r'\[Equation:', html_content))
        references = len(re.findall(r'\[\d+\]', html_content))
        return {
            "success": True,
            "formatted_html": html_content,
            "sections_detected": sections,
            "equations_found": equations,
            "references_found": references,
        }

    # Try Ollama first
    if _llm_chat is not None:
        try:
            html_content = _llm_chat(prompt, max_tokens=4000, temperature=0.2, top_p=0.9)
            if html_content:
                result = _parse_html_response(html_content.strip())
                result["provider"] = "ollama"
                return result
        except Exception as exc:
            print(f"⚠️ Ollama IEEE format failed: {exc}")

    # Groq fallback
    api_key = os.getenv("GROQ_API_KEY", "").strip()
    if not api_key or Groq is None:
        return None
    try:
        client = Groq(api_key=api_key)
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=4000,
        )
        html_content = response.choices[0].message.content.strip()
        result = _parse_html_response(html_content)
        result["provider"] = "groq"
        return result
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.post("/api/format-ieee")
def format_ieee(req: FormatIEEERequest) -> Dict[str, Any]:
    """Format raw text to IEEE paper structure using AI."""
    try:
        result = _format_ieee_with_ai(req.raw_text, req.format_type)
        
        if result and result.get("success"):
            return result
        
        # Fallback: basic formatting without AI
        lines = req.raw_text.strip().split('\n')
        html_parts = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Detect patterns
            if line.isupper() and len(line) < 100:
                html_parts.append(f"<h1>{line}</h1>")
            elif re.match(r'^[IVX]+\.\s', line):
                html_parts.append(f"<h1>{line}</h1>")
            elif re.match(r'^[A-Z]\.\s', line):
                html_parts.append(f"<h2>{line}</h2>")
            elif re.match(r'^\d+\)\s', line):
                html_parts.append(f"<p>{line}</p>")
            else:
                html_parts.append(f"<p>{line}</p>")
        
        return {
            "success": True,
            "formatted_html": "\n".join(html_parts),
            "sections_detected": len([p for p in html_parts if '<h1>' in p]),
            "equations_found": 0,
            "references_found": 0,
            "provider": "fallback",
            "error": result.get("error") if result else "AI unavailable"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


import subprocess
import tempfile
import base64
import shutil


@app.post("/api/compile-pdf")
def compile_pdf(req: CompilePDFRequest) -> Dict[str, Any]:
    """Compile LaTeX to PDF using pdflatex."""
    try:
        # Check if pdflatex is available
        pdflatex_path = shutil.which("pdflatex")
        if not pdflatex_path:
            return {
                "success": False,
                "error": "pdflatex not found. Install TeX Live or MiKTeX to enable PDF compilation.",
                "compilation_log": "pdflatex executable not found in PATH"
            }
        
        # Create temp directory
        with tempfile.TemporaryDirectory() as tmpdir:
            tex_file = os.path.join(tmpdir, "paper.tex")
            pdf_file = os.path.join(tmpdir, "paper.pdf")
            
            # Write LaTeX file
            with open(tex_file, 'w', encoding='utf-8') as f:
                f.write(req.latex_code)
            
            # Run pdflatex twice for references
            for _ in range(2):
                result = subprocess.run(
                    [pdflatex_path, "-interaction=nonstopmode", "-output-directory", tmpdir, tex_file],
                    capture_output=True,
                    text=True,
                    timeout=60
                )
            
            # Check if PDF was created
            if os.path.exists(pdf_file):
                with open(pdf_file, 'rb') as f:
                    pdf_bytes = f.read()
                
                return {
                    "success": True,
                    "pdf_base64": base64.b64encode(pdf_bytes).decode('utf-8'),
                    "compilation_log": result.stdout[-2000:] if result.stdout else ""
                }
            else:
                return {
                    "success": False,
                    "error": "PDF compilation failed",
                    "compilation_log": result.stdout[-2000:] if result.stdout else result.stderr[-2000:]
                }
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "error": "Compilation timeout (60s exceeded)",
            "compilation_log": ""
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "compilation_log": ""
        }


# =====================================================================
# GitHub-to-IEEE Endpoints
# =====================================================================


@app.post("/api/github-to-ieee", response_model=GitHubToIEEEResponse)
def github_to_ieee(req: GitHubToIEEERequest) -> GitHubToIEEEResponse:
    """Generate an IEEE-format paper from a GitHub repository."""
    try:
        result = github_paper_agent.run(
            repo_url=req.repo_url,
            author=req.author,
            institution=req.institution,
            max_files=req.max_files,
        )
        return GitHubToIEEEResponse(
            success=True,
            sections=result["sections"],
            pdf_base64=result["pdf_base64"],
            repo_name=result["repo_name"],
            analysis=result.get("analysis", {}),
        )
    except ValueError as e:
        return GitHubToIEEEResponse(success=False, error=str(e))
    except RuntimeError as e:
        return GitHubToIEEEResponse(success=False, error=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =====================================================================
# RAG Document Chat Endpoints
# =====================================================================


@app.post("/api/rag/sessions", response_model=RAGSessionResponse)
def rag_create_session() -> RAGSessionResponse:
    """Create a new RAG chat session."""
    try:
        result = rag_agent.create_session()
        return RAGSessionResponse(
            session_id=result["session_id"],
            name=result["name"],
            created_at=result["created_at"],
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/rag/sessions")
def rag_list_sessions() -> List[Dict[str, Any]]:
    """List all RAG chat sessions."""
    try:
        return rag_agent.list_sessions()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/rag/upload", response_model=RAGUploadResponse)
async def rag_upload(
    session_id: str = "",
    files: List[UploadFile] = File(...),
) -> RAGUploadResponse:
    """Upload documents to a RAG session for ingestion."""
    import tempfile as _tempfile

    if not session_id:
        raise HTTPException(status_code=400, detail="session_id is required")

    try:
        file_infos = []
        for upload in files:
            content = await upload.read()
            if not content:
                continue
            if len(content) > 20 * 1024 * 1024:
                continue  # Skip files > 20MB

            suffix = os.path.splitext(upload.filename or "")[1]
            tmp = _tempfile.NamedTemporaryFile(
                delete=False, suffix=suffix
            )
            tmp.write(content)
            tmp.close()

            file_infos.append(
                {
                    "path": tmp.name,
                    "filename": upload.filename or "unknown",
                    "content_type": upload.content_type or "",
                }
            )

        if not file_infos:
            return RAGUploadResponse(
                success=False, errors=["No valid files received."]
            )

        result = rag_agent.ingest_documents(session_id, file_infos)

        # Cleanup temp files
        for fi in file_infos:
            try:
                os.unlink(fi["path"])
            except Exception:
                pass

        return RAGUploadResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/rag/query", response_model=RAGQueryResponse)
def rag_query(req: RAGQueryRequest) -> RAGQueryResponse:
    """Ask a question about uploaded documents."""
    try:
        if not req.session_id or not req.question.strip():
            raise HTTPException(
                status_code=400, detail="session_id and question are required"
            )
        result = rag_agent.query(req.session_id, req.question.strip())
        return RAGQueryResponse(
            answer=result["answer"],
            sources=result["sources"],
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/rag/sessions/{session_id}/messages")
def rag_get_messages(session_id: str) -> List[Dict[str, Any]]:
    """Get chat history for a RAG session."""
    try:
        return rag_agent.get_messages(session_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/rag/sessions/{session_id}")
def rag_delete_session(session_id: str) -> Dict[str, Any]:
    """Delete a RAG chat session."""
    try:
        deleted = rag_agent.delete_session(session_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Session not found")
        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
