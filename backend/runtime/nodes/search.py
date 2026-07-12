"""
Search node — literature discovery.

Wraps the query-analysis agent + the reworked Search Agent (multi-source
retrieval with CrossRef, semantic dedup, and Citation Graph emission).
"""

from __future__ import annotations

from typing import Any, Dict

from backend.runtime import fields
from backend.runtime.nodes._base import node, query_agent, search_agent
from backend.runtime.state import PipelineState


@node("search")
def search_node(state: PipelineState) -> Dict[str, Any]:
    topic = state["topic"]
    constraints = state.get("constraints", {})

    # Discipline routing: map an explicitly chosen field to a source profile +
    # coarse domain. "general" (the default) is left unrouted so the Search Agent
    # keeps auto-classifying by keywords, preserving prior behavior.
    field, _subfield = fields.field_from_constraints(constraints)
    explicit_field = field != fields.DEFAULT_FIELD
    field_sources = fields.sources_for(field) if explicit_field else None
    field_domain = fields.domain_for(field) if explicit_field else None

    analysis = query_agent().run(topic, top_keywords=constraints.get("top_keywords", 8))
    keywords = analysis.get("keywords", []) or [topic]
    subtopics = analysis.get("subtopics", {}) or {}
    strategy = analysis.get("search_strategy", {}) or {}
    max_results = int(constraints.get("max_results", strategy.get("max_results", 8)))

    agent = search_agent()

    # Hybrid expansion → boolean query consolidation (Track A WordNet + Track B LLM).
    boolean_queries = []
    if constraints.get("use_boolean", True):
        try:
            from backend.core_agents.knowledge.thesaurus import expand_terms
            from backend.core_agents import query_builder
            track_a = expand_terms(keywords)
            track_b = query_builder.llm_expand(topic, keywords)
            boolean_queries = query_builder.build_boolean_queries(keywords, track_a, track_b)
        except Exception:
            boolean_queries = []

    if boolean_queries:
        retrieval = agent.retrieve_with_boolean_queries(
            boolean_queries, keywords, max_results=max_results, sources=field_sources
        )
    elif subtopics:
        retrieval = agent.retrieve_papers_multi_query(
            keywords, subtopics, max_results=max_results,
            domain=field_domain, sources=field_sources,
        )
    else:
        retrieval = agent.retrieve_papers(
            keywords, max_results=max_results,
            domain=field_domain, sources=field_sources,
        )

    if boolean_queries:
        analysis["boolean_queries"] = boolean_queries

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
