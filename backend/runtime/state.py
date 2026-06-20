"""
Shared pipeline state for the LangGraph runtime.

`PipelineState` is the single object threaded through every node. Nodes return
a partial dict of the keys they update; LangGraph merges those into the running
state. `warnings` and `errors` use additive reducers so multiple nodes can
append without clobbering each other.

The state is intentionally plain (TypedDict + JSON-serializable values) so it
can be returned directly in API responses and checkpointed to disk.
"""

from __future__ import annotations

import operator
import time
from typing import Annotated, Any, Dict, List, Optional
from typing_extensions import TypedDict


# Default control knobs for the revision loop (overridable per run / via env).
DEFAULT_MAX_REVISIONS = 2
DEFAULT_REVIEW_THRESHOLD = 7.0  # mean critic score (out of 10) required to pass


class PipelineState(TypedDict, total=False):
    """State shared across all pipeline nodes.

    `total=False` so nodes can populate keys incrementally. Every value must be
    JSON-serializable for API responses and checkpointing.
    """

    # ---- Inputs ----
    topic: str
    target_venue: str           # e.g. "IEEE", "ACM", "NeurIPS"
    output_type: str            # e.g. "survey", "research_paper", "report"
    constraints: Dict[str, Any]  # length, tone, citation_style, max_results, ...
    raw_materials: Dict[str, Any]  # notes, experimental logs, figures, templates

    # ---- Stage artifacts ----
    query_analysis: Dict[str, Any]      # Search: keywords, subtopics, strategy
    corpus: List[Dict[str, Any]]        # Search: retrieved + ranked papers
    citation_graph: Dict[str, Any]      # Search: shared knowledge source
    themes: Dict[str, Any]              # Topic Mining: clusters / taxonomy / gaps
    blueprint: Dict[str, Any]           # Outline: JSON section plan
    draft: Dict[str, Any]               # Drafting: per-section prose + latex
    review: Dict[str, Any]              # Review: scores, concerns, recommendation
    final_document: Dict[str, Any]      # Formatter: export artifacts

    # ---- Control / bookkeeping ----
    revision_count: int
    max_revisions: int
    review_threshold: float
    status: str                         # current stage label
    warnings: Annotated[List[str], operator.add]
    errors: Annotated[List[Dict[str, Any]], operator.add]
    stage_timings: Dict[str, float]     # stage -> seconds


def new_state(
    topic: str,
    *,
    target_venue: str = "IEEE",
    output_type: str = "research_paper",
    constraints: Optional[Dict[str, Any]] = None,
    raw_materials: Optional[Dict[str, Any]] = None,
    max_revisions: int = DEFAULT_MAX_REVISIONS,
    review_threshold: float = DEFAULT_REVIEW_THRESHOLD,
) -> PipelineState:
    """Build a fresh `PipelineState` with sane defaults."""
    return PipelineState(
        topic=topic,
        target_venue=target_venue,
        output_type=output_type,
        constraints=constraints or {},
        raw_materials=raw_materials or {},
        query_analysis={},
        corpus=[],
        citation_graph={},
        themes={},
        blueprint={},
        draft={},
        review={},
        final_document={},
        revision_count=0,
        max_revisions=max_revisions,
        review_threshold=review_threshold,
        status="initialized",
        warnings=[],
        errors=[],
        stage_timings={},
    )


def mark_timing(state: PipelineState, stage: str, started_at: float) -> Dict[str, float]:
    """Return a merged stage_timings dict recording elapsed seconds for `stage`."""
    timings = dict(state.get("stage_timings", {}))
    timings[stage] = round(time.time() - started_at, 3)
    return timings
