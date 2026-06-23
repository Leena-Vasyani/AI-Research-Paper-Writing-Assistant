from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    text: str = Field(..., description="Research topic or query text")
    top_keywords: int = Field(8, ge=3, le=20)


class KeywordItem(BaseModel):
    text: str = ""
    score: float = 0.0
    type: str = "core"


class KeywordExtractRequest(BaseModel):
    text: str = Field(..., description="Text to extract keywords from")
    top_n: int = Field(8, ge=1, le=20)
    use_llm: bool = Field(True, description="Use LLM for semantic extraction")
    expand_acronyms: bool = Field(True, description="Expand detected acronyms")
    return_synonyms: bool = Field(False, description="Generate synonym variants")


class KeywordExtractResponse(BaseModel):
    keywords: List[KeywordItem] = Field(default_factory=list)
    synonyms: Dict[str, List[str]] = Field(default_factory=dict)
    provider: str = "fallback"
    elapsed_ms: int = 0


class SearchStrategy(BaseModel):
    max_results: int = 5
    use_multi_query: bool = False
    sources: List[str] = Field(default_factory=lambda: ["arxiv", "openalex", "semantic_scholar"])
    recommended_top_keywords: int = 8


class QueryResponse(BaseModel):
    original_topic: str = ""
    keywords: List[str] = Field(default_factory=list)
    subtopics: Dict[str, List[str]] = Field(default_factory=dict)
    complexity_analysis: Dict[str, Any] = Field(default_factory=dict)
    intent: str = "informational"
    intent_confidence: float = 0.0
    sub_queries: List[str] = Field(default_factory=list)
    synonyms: Dict[str, List[str]] = Field(default_factory=dict)
    domain_specificity_score: float = 0.0
    scope: str = "narrow"
    search_strategy: SearchStrategy = Field(default_factory=SearchStrategy)
    keyword_details: List[KeywordItem] = Field(default_factory=list)
    elapsed_ms: int = 0


class RetrieveRequest(BaseModel):
    keywords: List[str]
    max_results: int = Field(5, ge=1, le=20)
    use_multi_query: bool = False
    subtopics: Optional[Dict[str, List[str]]] = None
    sources: Optional[List[str]] = None
    domain: Optional[str] = Field(
        None,
        description="Force domain routing: 'health' | 'cs' | 'general'. Auto-detected if omitted."
    )


class RetrieveResponse(BaseModel):
    papers: List[Dict[str, Any]] = Field(default_factory=list)
    domain: str = "general"
    source_status: Dict[str, str] = Field(default_factory=dict)
    total: int = 0
    query: str = ""
    warnings: Optional[List[str]] = None


class SummarizeRequest(BaseModel):
    papers: List[Dict[str, Any]]
    keywords: List[str]


class DraftConfigRequest(BaseModel):
    max_new_tokens: int = Field(600, ge=200, le=1200)
    min_new_tokens: int = Field(300, ge=100, le=800)
    temperature: float = Field(0.7, ge=0.0, le=1.5)
    top_p: float = Field(0.9, ge=0.1, le=1.0)
    repetition_penalty: float = Field(1.2, ge=1.0, le=2.0)
    num_beams: int = Field(4, ge=1, le=8)
    no_repeat_ngram_size: int = Field(3, ge=0, le=5)


class DraftRequest(BaseModel):
    research_topic: str
    comprehensive_summary: Dict[str, Any]
    keywords: List[str]
    config: Optional[DraftConfigRequest] = None


class PlagiarismRequest(BaseModel):
    generated_draft: Dict[str, str]
    source_papers: List[Dict[str, Any]]
    research_topic: str


class RefineBlockRequest(BaseModel):
    text: str = Field(..., description="Block text to refine")
    mode: str = Field("refine", description="expand|academic|refine|anti_plagiarism")
    source_texts: List[str] = Field(
        default_factory=list,
        description="Optional source texts used to reduce lexical overlap",
    )


class AutocompleteRequest(BaseModel):
    text: str = Field("", description="Current editor text")
    max_suggestions: int = Field(3, ge=1, le=8)


class AutocompleteResponse(BaseModel):
    suggestions: List[str] = Field(default_factory=list)
    provider: str = Field("fallback")


class DiagramRequest(BaseModel):
    description: str = Field(..., description="Text description for diagram")
    diagram_type: str = Field("auto", description="Optional diagram type hint")


class CitationRequest(BaseModel):
    draft: Dict[str, str] = Field(..., description="Draft sections to cite")
    papers: List[Dict[str, Any]] = Field(..., description="Source papers for citations")
    style: str = Field("apa", description="Citation style: apa|ieee|mla")
    plagiarism_results: Optional[Dict[str, Any]] = None
    
class PseudocodeRequest(BaseModel):
    code: str = Field(..., description="Source code to convert")
    algorithm_name: str = Field("", description="Optional algorithm name for caption")


class FormatCommand(BaseModel):
    target: str = Field(..., description="Target section or selection")
    action: str = Field(..., description="Editor action to perform")


class FormatCommandRequest(BaseModel):
    prompt: str = Field(..., description="User prompt for layout changes")
    settings: Dict[str, Any] = Field(default_factory=dict)
    available_targets: List[str] = Field(default_factory=list)


class FormatCommandResponse(BaseModel):
    cssUpdates: Dict[str, Any] = Field(default_factory=dict)
    editorCommands: List[FormatCommand] = Field(default_factory=list)
    provider: str = Field("fallback")


class PseudocodeRequest(BaseModel):
    code: str = Field(..., description="Source code to convert")
    algorithm_name: str = Field("", description="Optional algorithm name for caption")


class FormatIEEERequest(BaseModel):
    raw_text: str = Field(..., description="Raw research paper text to format")
    format_type: str = Field("conference", description="IEEE format: conference|journal|transactions")
    detect_equations: bool = Field(True, description="Auto-detect and format equations")
    detect_references: bool = Field(True, description="Auto-detect and format references")


class CompilePDFRequest(BaseModel):
    latex_code: str = Field(..., description="LaTeX code to compile to PDF")


class CitationSuggestRequest(BaseModel):
    claim_text: str = Field(..., description="Claim sentence/selection to support with citations")
    context_text: str = Field("", description="Optional surrounding context for better matching")
    citation_style: str = Field("apa", description="Citation style: apa|ieee|mla")
    max_candidates: int = Field(3, ge=1, le=10)
    keywords: List[str] = Field(default_factory=list, description="Optional retrieval keywords")
    provided_papers: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Optional papers to match against; retrieval used when empty",
    )
    auto_retrieve: bool = Field(
        True,
        description="Automatically retrieve papers if provided_papers is empty",
    )
    retrieve_max_results: int = Field(8, ge=1, le=20)


class CitationFormatRequest(BaseModel):
    paper: Dict[str, Any] = Field(..., description="Paper metadata used for citation formatting")
    citation_style: str = Field("apa", description="Citation style: apa|ieee|mla")
    citation_number: Optional[int] = Field(None, ge=1)


class CitationCandidate(BaseModel):
    title: str = ""
    authors: str = ""
    year: str = ""
    source: str = ""
    doi_or_url: str = ""
    relevance_score: float = 0.0
    citation_type: str = "general"
    in_text: str = ""
    reference: str = ""


class CitationSuggestResponse(BaseModel):
    success: bool = True
    claim_text: str = ""
    citation_style: str = "apa"
    candidates: List[CitationCandidate] = Field(default_factory=list)
    confidence: float = 0.0
    source_count: int = 0
    notes: List[str] = Field(default_factory=list)


class ExtractTextResponse(BaseModel):
    success: bool = True
    text: str = ""
    filename: str = ""
    extension: str = ""
    warnings: List[str] = Field(default_factory=list)


# ── GitHub-to-IEEE ────────────────────────────────────────────────────

class GitHubToIEEERequest(BaseModel):
    repo_url: str = Field(..., description="GitHub repository URL")
    author: str = Field("", description="Author name for the paper")
    institution: str = Field("", description="Institution / affiliation")
    max_files: int = Field(40, ge=5, le=100, description="Maximum repo files to analyse")


class GitHubToIEEEResponse(BaseModel):
    success: bool = True
    sections: Dict[str, str] = Field(default_factory=dict)
    pdf_base64: str = ""
    repo_name: str = ""
    analysis: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None


# ── Q&A Agent (research-level questions + grounded answers) ───────────

class QARequest(BaseModel):
    topic: str = Field(..., description="Research topic / user query")
    corpus: List[Dict[str, Any]] = Field(
        default_factory=list, description="Fetched papers (title/abstract/...)"
    )
    themes: Dict[str, Any] = Field(
        default_factory=dict, description="Optional mined themes/gaps from topic mining"
    )
    max_questions: int = Field(6, description="Number of questions to generate")


class QAResponse(BaseModel):
    questions: List[str] = Field(default_factory=list)
    qa_pairs: List[Dict[str, Any]] = Field(default_factory=list)
    method: str = ""


# ── RAG Document Chat ─────────────────────────────────────────────────

class RAGQueryRequest(BaseModel):
    session_id: str = Field(..., description="Chat session ID")
    question: str = Field(..., description="User question")


class RAGQueryResponse(BaseModel):
    answer: str = ""
    sources: List[Dict[str, Any]] = Field(default_factory=list)


class RAGSessionResponse(BaseModel):
    session_id: str = ""
    name: str = ""
    created_at: str = ""


class RAGSessionListItem(BaseModel):
    id: str = ""
    name: str = ""
    created_at: str = ""
    last_active: str = ""
    document_count: int = 0


class RAGMessageResponse(BaseModel):
    role: str = ""
    content: str = ""
    sources: List[Dict[str, Any]] = Field(default_factory=list)
    created_at: str = ""


class RAGUploadResponse(BaseModel):
    success: bool = True
    processed: int = 0
    chunks: int = 0
    errors: List[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Multi-agent pipeline (LangGraph runtime)
# ---------------------------------------------------------------------------


class PipelineRunRequest(BaseModel):
    topic: str = Field(..., description="Research topic / query")
    target_venue: str = Field("IEEE", description="Target venue: IEEE / ACM / ...")
    output_type: str = Field("research_paper", description="research_paper / survey / report")
    constraints: Dict[str, Any] = Field(default_factory=dict,
                                        description="max_results, citation_style, top_keywords, ...")
    raw_materials: Dict[str, Any] = Field(default_factory=dict,
                                          description="notes, logs, figures, latex_template")
    max_revisions: int = Field(2, ge=0, le=5)
    review_threshold: float = Field(7.0, ge=0.0, le=10.0)


class PipelineStageRequest(BaseModel):
    stage: str = Field(..., description="search|topic_mining|outline|drafting|review|citation|formatter")
    state: Dict[str, Any] = Field(default_factory=dict,
                                  description="Accumulated pipeline state to run the stage on")

