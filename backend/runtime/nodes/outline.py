"""
Outline node — produce the JSON Blueprint that drives drafting.

Phase 0: emits a minimal blueprint matching the current draft sections
(abstract / introduction / related_work) so the pipeline runs end-to-end.
Phase 3 replaces this with the full Outline Agent (small-model cues ->
LLM section plan -> delta-feedback loop, 8 sections / ~4 subsections,
citation hints, visualization directives, template parsing).
"""

from __future__ import annotations

from typing import Any, Dict

from backend.runtime.nodes._base import node
from backend.runtime.state import PipelineState

# Minimal default structure for the Phase 0 stub.
_DEFAULT_SECTIONS = ["abstract", "introduction", "related_work"]


@node("outline")
def outline_node(state: PipelineState) -> Dict[str, Any]:
    themes = state.get("themes", {})
    sections = [
        {
            "name": name,
            "subsections": [],
            "citation_hints": [],
            "visualization_directives": [],
        }
        for name in _DEFAULT_SECTIONS
    ]
    blueprint = {
        "topic": state["topic"],
        "target_venue": state.get("target_venue", "IEEE"),
        "output_type": state.get("output_type", "research_paper"),
        "sections": sections,
        "themes": themes.get("clusters", []),
        "_stub": True,  # replaced in Phase 3
    }
    return {"blueprint": blueprint}
