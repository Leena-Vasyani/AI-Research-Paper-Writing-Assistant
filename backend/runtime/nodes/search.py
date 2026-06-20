"""
Search node — literature discovery.

Wraps the query-analysis agent + the reworked Search Agent (multi-source
retrieval with CrossRef, semantic dedup, and Citation Graph emission).
"""

from __future__ import annotations

from typing import Any, Dict

from backend.runtime.nodes._base import node, query_agent, search_agent
from backend.runtime.state import PipelineState


@node("search")
def search_node(state: PipelineState) -> Dict[str, Any]:
    topic = state["topic"]
    constraints = state.get("constraints", {})

    analysis = query_agent().run(topic, top_keywords=constraints.get("top_keywords", 8))
    keywords = analysis.get("keywords", []) or [topic]
    subtopics = analysis.get("subtopics", {}) or {}
    strategy = analysis.get("search_strategy", {}) or {}
    max_results = int(constraints.get("max_results", strategy.get("max_results", 8)))

    if subtopics:
        retrieval = search_agent().retrieve_papers_multi_query(
            keywords, subtopics, max_results=max_results
        )
    else:
        retrieval = search_agent().retrieve_papers(keywords, max_results=max_results)

    if isinstance(retrieval, dict):
        papers = retrieval.get("papers", [])
        warnings = retrieval.get("warnings", [])
        citation_graph = retrieval.get("citation_graph", {})
    else:
        papers, warnings, citation_graph = (retrieval or []), [], {}

    update: Dict[str, Any] = {
        "query_analysis": analysis,
        "corpus": papers,
        "citation_graph": citation_graph or {},
    }
    if warnings:
        update["warnings"] = list(warnings)
    return update
