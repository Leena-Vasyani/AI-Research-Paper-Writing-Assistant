"""
LangGraph pipeline builder.

Wires the agent nodes into a state machine:

    START -> search -> topic_mining -> outline -> drafting -> review
    review --(revise)--> drafting        (conditional revision loop)
    review --(proceed)--> citation -> formatter -> END

The revision loop matches the PDR ``GenerateResearchArtifact`` control flow:
revise while quality is below threshold or critical issues remain, capped by
``max_revisions``.
"""

from __future__ import annotations

from typing import Any, Optional

from langgraph.graph import StateGraph, START, END

from backend.runtime import nodes
from backend.runtime.state import (
    PipelineState,
    new_state,
    DEFAULT_MAX_REVISIONS,
    DEFAULT_REVIEW_THRESHOLD,
)


def _after_review(state: PipelineState) -> str:
    """Conditional edge: revise the draft or proceed to citation/export."""
    review = state.get("review", {})
    mean_score = float(review.get("mean_score", 0.0) or 0.0)
    threshold = float(state.get("review_threshold", DEFAULT_REVIEW_THRESHOLD))
    passed = mean_score >= threshold and not review.get("has_critical_issues", False)
    exhausted = state.get("revision_count", 0) >= state.get("max_revisions", DEFAULT_MAX_REVISIONS)
    return "proceed" if (passed or exhausted) else "revise"


def build_pipeline_graph():
    """Compile and return the runnable pipeline graph."""
    graph = StateGraph(PipelineState)

    graph.add_node("search", nodes.search_node)
    graph.add_node("topic_mining", nodes.topic_mining_node)
    graph.add_node("outline", nodes.outline_node)
    graph.add_node("drafting", nodes.drafting_node)
    graph.add_node("review", nodes.review_node)
    graph.add_node("citation", nodes.citation_node)
    graph.add_node("formatter", nodes.formatter_node)

    graph.add_edge(START, "search")
    graph.add_edge("search", "topic_mining")
    graph.add_edge("topic_mining", "outline")
    graph.add_edge("outline", "drafting")
    graph.add_edge("drafting", "review")
    graph.add_conditional_edges(
        "review",
        _after_review,
        {"revise": "drafting", "proceed": "citation"},
    )
    graph.add_edge("citation", "formatter")
    graph.add_edge("formatter", END)

    return graph.compile()


def run_pipeline(topic: str, *, config: Optional[dict] = None, **kwargs: Any) -> PipelineState:
    """Convenience entrypoint: build the graph and run it for ``topic``."""
    graph = build_pipeline_graph()
    state = new_state(topic, **kwargs)
    # recursion_limit guards against runaway revision loops at the graph level.
    run_config = {"recursion_limit": 50}
    if config:
        run_config.update(config)
    return graph.invoke(state, config=run_config)
