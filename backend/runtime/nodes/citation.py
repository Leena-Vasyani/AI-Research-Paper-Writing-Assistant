"""
Citation node — grounding gate.

Attaches citations and audits every factual/numeric/comparison claim for
provenance against the corpus / Citation Graph (PDR §11). Claims without a
supporting source are flagged as *blocked* and the result records whether the
draft is export-ready.
"""

from __future__ import annotations

from typing import Any, Dict

from backend.runtime.nodes._base import node, citation_agent
from backend.runtime.state import PipelineState


@node("citation")
def citation_node(state: PipelineState) -> Dict[str, Any]:
    draft = dict(state.get("draft", {}))
    sections = draft.get("sections", {})
    corpus = state.get("corpus", [])
    citation_graph = state.get("citation_graph", {})
    citation_style = state.get("constraints", {}).get("citation_style", "ieee")

    result = citation_agent().ground_draft(
        sections,
        corpus,
        citation_graph=citation_graph,
        citation_style=citation_style,
    )
    draft["cited"] = result

    update: Dict[str, Any] = {"draft": draft}
    grounding = result.get("grounding", {})
    if not grounding.get("export_ready", True):
        update["warnings"] = [
            f"{len(grounding.get('blocked', []))} factual claim(s) lack provenance"
        ]
    return update
