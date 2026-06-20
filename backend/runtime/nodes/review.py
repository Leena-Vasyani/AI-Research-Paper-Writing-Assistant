"""
Review node — multi-critic peer review of the draft.

Delegates to the ReviewAgent (Novelty / Coherence / Logical Consistency /
Evidence Quality / Unsupported Claims / Writing & Reproducibility, plus the
plagiarism agent folded in as an originality critic). Emits per-axis scores,
``mean_score`` and ``has_critical_issues`` (consumed by the graph's revision
conditional), major concerns, a recommendation, and structured critique.
"""

from __future__ import annotations

from typing import Any, Dict

from backend.runtime.nodes._base import node, review_agent
from backend.runtime.state import PipelineState


@node("review")
def review_node(state: PipelineState) -> Dict[str, Any]:
    draft = state.get("draft", {})
    review = review_agent().review(
        draft,
        topic=state["topic"],
        corpus=state.get("corpus", []),
        citation_graph=state.get("citation_graph", {}),
        blueprint=state.get("blueprint", {}),
    )
    return {"review": review}
