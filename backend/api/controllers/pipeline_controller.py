"""
Pipeline controller.

Bridges the HTTP layer and the LangGraph runtime: runs the full orchestrated
pipeline, or a single stage for human-in-the-loop stepping (outline approval,
section edits, re-review, ...). Keeps the graph compiled once and reused.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from backend.runtime import nodes
from backend.runtime.graph import build_pipeline_graph
from backend.runtime.state import PipelineState, new_state

# Ordered stage map (mirrors the graph topology, minus the revision edge).
STAGE_FNS = {
    "search": nodes.search_node,
    "topic_mining": nodes.topic_mining_node,
    "qa": nodes.qa_node,
    "outline": nodes.outline_node,
    "drafting": nodes.drafting_node,
    "review": nodes.review_node,
    "citation": nodes.citation_node,
    "formatter": nodes.formatter_node,
}
STAGE_ORDER = list(STAGE_FNS.keys())

_GRAPH = None


def _graph():
    global _GRAPH
    if _GRAPH is None:
        _GRAPH = build_pipeline_graph()
    return _GRAPH


def run_full(
    topic: str,
    *,
    target_venue: str = "IEEE",
    output_type: str = "research_paper",
    constraints: Optional[Dict[str, Any]] = None,
    raw_materials: Optional[Dict[str, Any]] = None,
    max_revisions: int = 2,
    review_threshold: float = 7.0,
) -> Dict[str, Any]:
    """Run the entire pipeline and return the final serialized state."""
    state = new_state(
        topic,
        target_venue=target_venue,
        output_type=output_type,
        constraints=constraints or {},
        raw_materials=raw_materials or {},
        max_revisions=max_revisions,
        review_threshold=review_threshold,
    )
    # run_name + metadata surface as a named, filterable trace in LangSmith
    # (LangGraph auto-emits node/edge spans when tracing is enabled).
    config = {
        "recursion_limit": 50,
        "run_name": "research_pipeline",
        "metadata": {
            "topic": topic,
            "output_type": output_type,
            "target_venue": target_venue,
        },
    }
    result = _graph().invoke(state, config=config)
    return dict(result)


def run_stage(stage: str, state: Dict[str, Any]) -> Dict[str, Any]:
    """Run a single stage on the provided state (for HITL stepping).

    Returns the merged state. Additive fields (warnings/errors) are appended
    rather than replaced so stepping accumulates them like the graph would.
    """
    if stage not in STAGE_FNS:
        raise ValueError(f"unknown stage '{stage}'. valid: {STAGE_ORDER}")

    # Seed any missing keys with defaults so a node never sees an absent field.
    base = new_state(state.get("topic", ""))
    base.update(state)  # type: ignore[arg-type]

    update = STAGE_FNS[stage](base) or {}
    
    merged: Dict[str, Any] = dict(base)
    for key, value in update.items():
        if key in ("warnings", "errors") and isinstance(value, list):
            merged[key] = list(merged.get(key, [])) + value
        else:
            merged[key] = value
    return merged
