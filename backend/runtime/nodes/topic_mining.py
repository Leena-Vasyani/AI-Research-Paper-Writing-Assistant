"""
Topic Mining node — cluster the retrieved corpus into themes / taxonomy / gaps.

Phase 0: pass-through stub that derives coarse themes from the query analysis
subtopics so the Outline node has structured input. Phase 2 replaces this with
real corpus embedding + clustering (SentenceTransformer/FAISS via rag_agent).
"""

from __future__ import annotations

from typing import Any, Dict

from backend.runtime.nodes._base import node
from backend.runtime.state import PipelineState


@node("topic_mining")
def topic_mining_node(state: PipelineState) -> Dict[str, Any]:
    analysis = state.get("query_analysis", {})
    subtopics = analysis.get("subtopics", {}) or {}
    corpus = state.get("corpus", [])

    clusters = [
        {"theme": name, "keywords": kws, "paper_count": len(corpus)}
        for name, kws in subtopics.items()
    ]
    if not clusters:
        clusters = [{"theme": state["topic"], "keywords": analysis.get("keywords", []),
                     "paper_count": len(corpus)}]

    themes = {
        "clusters": clusters,
        "taxonomy": list(subtopics.keys()),
        "gaps": analysis.get("research_gaps", []),
        "_stub": True,  # replaced in Phase 2
    }
    return {"themes": themes}
