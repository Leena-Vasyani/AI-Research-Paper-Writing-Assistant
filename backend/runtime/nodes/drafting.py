"""
Drafting node — produce manuscript sections from the blueprint + corpus.

Phase 0: wraps the existing summarization + fine-tuned drafting agents so the
pipeline produces a real draft end-to-end. Phase 4 replaces this with the
LLM+FAISS parallel section writer (per-section ~1000 words, 25% ref cap,
body-first ordering, LaTeX render); the fine-tuned model becomes a fallback.

This node also drives the revision loop: when a prior ``review`` exists in
state, it counts as a re-draft and increments ``revision_count``.
"""

from __future__ import annotations

from typing import Any, Dict

from backend.runtime.nodes._base import node, summarization_agent, drafting_agent
from backend.runtime.state import PipelineState


@node("drafting")
def drafting_node(state: PipelineState) -> Dict[str, Any]:
    topic = state["topic"]
    corpus = state.get("corpus", [])
    analysis = state.get("query_analysis", {})
    keywords = analysis.get("keywords", []) or [topic]

    # Reuse a prior comprehensive summary across revisions to save work.
    prior_draft = state.get("draft", {})
    summary = prior_draft.get("comprehensive_summary")
    if not summary:
        summary = summarization_agent().generate_comprehensive_summary(corpus, keywords)

    sections = drafting_agent().generate_complete_draft(topic, summary, keywords)

    draft: Dict[str, Any] = {
        "sections": sections,
        "comprehensive_summary": summary,
    }

    update: Dict[str, Any] = {"draft": draft}
    # A pre-existing review means we looped back here to revise.
    if state.get("review"):
        update["revision_count"] = state.get("revision_count", 0) + 1
    return update
