"""
Outline node — produce the JSON Blueprint that drives drafting.

Delegates to the OutlineAgent: deterministic skeleton (always valid) enriched
with small-model section cues, then a delta-feedback coverage pass. Consumes the
themes (Topic Mining), corpus + Citation Graph (Search), and any raw materials
(notes / conference LaTeX template) from state.
"""

from __future__ import annotations

from typing import Any, Dict

from backend.runtime.nodes._base import node, outline_agent
from backend.runtime.state import PipelineState


@node("outline")
def outline_node(state: PipelineState) -> Dict[str, Any]:
    blueprint = outline_agent().build(
        state["topic"],
        themes=state.get("themes", {}),
        corpus=state.get("corpus", []),
        citation_graph=state.get("citation_graph", {}),
        target_venue=state.get("target_venue", "IEEE"),
        output_type=state.get("output_type", "research_paper"),
        raw_materials=state.get("raw_materials", {}),
        constraints=state.get("constraints", {}),
    )
    return {"blueprint": blueprint}
