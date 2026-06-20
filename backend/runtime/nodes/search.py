"""
Search node — literature discovery.

Phase 0: wraps the existing query-analysis + multi-source retrieval agents.
Phase 1 replaces the agent internals (CrossRef source, Citation Graph,
stronger semantic dedup) without changing this node's contract.
"""

from __future__ import annotations

from typing import Any, Dict

from backend.runtime.nodes._base import node, query_agent, retrieval_agent
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
        retrieval = retrieval_agent().retrieve_papers_multi_query(
            keywords, subtopics, max_results=max_results
        )
    else:
        retrieval = retrieval_agent().retrieve_papers(keywords, max_results=max_results)

    papers = retrieval.get("papers", []) if isinstance(retrieval, dict) else (retrieval or [])
    warnings = retrieval.get("warnings", []) if isinstance(retrieval, dict) else []

    update: Dict[str, Any] = {
        "query_analysis": analysis,
        "corpus": papers,
        # citation_graph populated in Phase 1; keep the key present for downstream nodes
        "citation_graph": state.get("citation_graph") or {},
    }
    if warnings:
        update["warnings"] = list(warnings)
    return update
