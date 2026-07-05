"""
Drafting node — produce the manuscript from the blueprint + corpus.

Delegates to the new DraftingAgent: parallel section dispatch, FAISS retrieval
(capped per section), data extraction, body-first ordering, per-section verify +
delta-feedback refine, and LaTeX rendering.

Also drives the revision loop: when a prior ``review`` exists in state, this is
a re-draft, so ``revision_count`` is incremented and the review's concerns are
passed back into generation as feedback.
"""

from __future__ import annotations

from typing import Any, Dict

from backend.runtime import humanize
from backend.runtime.nodes._base import node, drafting_agent
from backend.runtime.state import PipelineState


@node("drafting")
def drafting_node(state: PipelineState) -> Dict[str, Any]:
    blueprint = state.get("blueprint", {})
    corpus = state.get("corpus", [])
    review = state.get("review", {})

    result = drafting_agent().draft(
        blueprint,
        corpus,
        topic=state["topic"],
        raw_materials=state.get("raw_materials", {}),
        constraints=state.get("constraints", {}),
        review_feedback=review or None,
        qa=state.get("qa", {}),
    )

    sections = result.get("sections", {})
    draft: Dict[str, Any] = {
        "title": result.get("title", ""),
        "sections": sections,
        "latex": result.get("latex", ""),
        "section_meta": result.get("section_meta", {}),
        "references_used": result.get("references_used", []),
        "method": result.get("method", ""),
    }

    # Stamp the humanization baseline on every draft run (pipeline / workflow /
    # agent-hub all read this): a pristine copy of the generated sections plus the
    # per-section edit quota, so the UI gate and /api/humanize/validate share one
    # authoritative baseline. A revision-loop re-draft simply re-stamps a fresh one.
    fraction = float(
        state.get("constraints", {}).get("humanize_fraction", humanize.DEFAULT_FRACTION)
    )
    draft["original_sections"] = dict(sections)
    draft["humanize"] = humanize.build_humanize_meta(sections, fraction, blueprint)

    update: Dict[str, Any] = {"draft": draft}
    # A pre-existing review means we looped back here to revise.
    if review:
        update["revision_count"] = state.get("revision_count", 0) + 1
    return update
