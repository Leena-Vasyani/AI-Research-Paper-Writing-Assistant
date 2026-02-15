from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    text: str = Field(..., description="Research topic or query text")
    top_keywords: int = Field(8, ge=3, le=20)


class RetrieveRequest(BaseModel):
    keywords: List[str]
    max_results: int = Field(5, ge=1, le=20)
    use_multi_query: bool = False
    subtopics: Optional[Dict[str, List[str]]] = None
    sources: Optional[List[str]] = None


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

