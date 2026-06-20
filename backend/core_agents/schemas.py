"""
Pydantic output models for the Search and Topic Mining agents.

These provide typed, validated contracts (per the agent spec) layered on top of
the existing dict outputs. Agents expose `*_models()` accessors; the runtime
nodes keep using `.model_dump()` dicts so `PipelineState` / FastAPI are
unaffected (additive, non-breaking).
"""

from __future__ import annotations

from typing import Any, Dict, List

from pydantic import BaseModel, Field


def _as_list(v: Any) -> List[str]:
    if isinstance(v, list):
        return [str(x) for x in v]
    if isinstance(v, str) and v:
        return [v]
    return []


class PaperModel(BaseModel):
    title: str = ""
    authors: List[str] = Field(default_factory=list)
    abstract: str = ""
    published: str = ""
    url: str = ""
    pdf_url: str = ""
    doi: str = ""
    source: str = ""
    citations: int = 0
    relevance_score: float = 0.0

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "PaperModel":
        return cls(
            title=d.get("title", "") or "",
            authors=_as_list(d.get("authors")),
            abstract=d.get("abstract", "") or "",
            published=str(d.get("published", "") or ""),
            url=d.get("url", "") or "",
            pdf_url=d.get("pdf_url", "") or "",
            doi=d.get("doi", "") or "",
            source=d.get("source", "") or "",
            citations=int(d.get("citations", 0) or 0),
            relevance_score=float(d.get("relevance_score", 0) or 0),
        )


class RankedCorpus(BaseModel):
    """Search Agent output — the ranked paper corpus."""
    query: str = ""
    domain: str = ""
    total: int = 0
    papers: List[PaperModel] = Field(default_factory=list)

    @classmethod
    def from_result(cls, r: Dict[str, Any]) -> "RankedCorpus":
        papers = [PaperModel.from_dict(p) for p in (r.get("papers") or [])]
        return cls(
            query=r.get("query", "") or "",
            domain=r.get("domain", "") or "",
            total=len(papers),
            papers=papers,
        )


class PaperAttributes(BaseModel):
    """SLM-extracted focus attributes for a single abstract."""
    core_methodology: str = ""
    primary_problem_domain: str = ""
    key_contribution: str = ""

    def focused_text(self) -> str:
        parts = [self.core_methodology, self.primary_problem_domain, self.key_contribution]
        return ". ".join(p for p in parts if p).strip()


class TopicCluster(BaseModel):
    id: int = 0
    theme: str = ""
    keywords: List[str] = Field(default_factory=list)
    size: int = 0
    paper_titles: List[str] = Field(default_factory=list)


class TopicMiningResult(BaseModel):
    """Topic Mining output — clusters, taxonomy, gaps, metrics."""
    method: str = ""
    clusters: List[TopicCluster] = Field(default_factory=list)
    taxonomy: List[str] = Field(default_factory=list)
    gaps: List[str] = Field(default_factory=list)
    metrics: Dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_result(cls, r: Dict[str, Any]) -> "TopicMiningResult":
        clusters = [
            TopicCluster(
                id=c.get("id", i),
                theme=c.get("theme", ""),
                keywords=c.get("keywords", []) or [],
                size=c.get("size", 0),
                paper_titles=c.get("papers", []) or [],
            )
            for i, c in enumerate(r.get("clusters", []) or [])
        ]
        return cls(
            method=r.get("method", ""),
            clusters=clusters,
            taxonomy=r.get("taxonomy", []) or [],
            gaps=r.get("gaps", []) or [],
            metrics=r.get("metrics", {}) or {},
        )
