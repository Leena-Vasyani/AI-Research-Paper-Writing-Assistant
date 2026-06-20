"""
Review node — score the draft and decide whether to revise.

Phase 0: wraps the existing plagiarism agent and maps its originality score
onto a 0-10 quality scale so the revision loop's conditional edge has a signal.
Phase 5 replaces this with the multi-critic Review Agent (Novelty, Coherence,
Logical Consistency, Evidence Quality, Unsupported Claims, Writing/
Reproducibility) and folds plagiarism in as one originality critic.
"""

from __future__ import annotations

from typing import Any, Dict

from backend.runtime.nodes._base import node, plagiarism_agent
from backend.runtime.state import PipelineState


@node("review")
def review_node(state: PipelineState) -> Dict[str, Any]:
    draft = state.get("draft", {})
    sections = draft.get("sections", {})
    corpus = state.get("corpus", [])
    topic = state["topic"]

    report = plagiarism_agent().check_plagiarism(sections, corpus, topic)

    # Plagiarism overall_score is 0-1 (higher = more overlap = worse).
    overlap = float(report.get("overall_score", 0.0) or 0.0)
    originality_score = round(max(0.0, (1.0 - overlap)) * 10.0, 1)
    has_critical = report.get("overall_status") == "high"

    review = {
        "scores": {"originality": originality_score},
        "mean_score": originality_score,
        "has_critical_issues": has_critical,
        "recommendation": "weak_accept" if not has_critical else "revise",
        "major_concerns": [
            s["section_name"]
            for s in report.get("section_analyses", [])
            if s.get("status") == "high"
        ],
        "plagiarism": report,
        "_stub": True,  # replaced in Phase 5
    }
    return {"review": review}
