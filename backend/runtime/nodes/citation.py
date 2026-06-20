"""
Citation node — attach grounded citations to the draft.

Phase 0: wraps the existing citation agent. Phase 6 reworks this into the
provenance/grounding gate (every factual/numeric claim must resolve against
the corpus / Citation Graph before export).
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
    review = state.get("review", {})
    citation_style = state.get("constraints", {}).get("citation_style", "ieee")

    cited = citation_agent().add_citations_to_draft(
        sections,
        corpus,
        plagiarism_results=review.get("plagiarism"),
        citation_style=citation_style,
    )
    draft["cited"] = cited
    return {"draft": draft}
