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
    mode: str = Field("refine", description="expand|academic|refine")


class DiagramRequest(BaseModel):
    description: str = Field(..., description="Text description for diagram")
    diagram_type: str = Field("auto", description="Optional diagram type hint")


class CitationRequest(BaseModel):
    draft: Dict[str, str] = Field(..., description="Draft sections to cite")
    papers: List[Dict[str, Any]] = Field(..., description="Source papers for citations")
    style: str = Field("apa", description="Citation style: apa|ieee|mla")
    plagiarism_results: Optional[Dict[str, Any]] = None
