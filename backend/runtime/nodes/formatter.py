"""
Formatter node — assemble the final exportable artifact.

Phase 0: assembles the cited draft into a simple structured document. Phase 6
replaces this with the unified Formatter Agent (LaTeX/DOCX/Markdown export,
diagrams, pseudocode, plotting directives from the blueprint).
"""

from __future__ import annotations

from typing import Any, Dict

from backend.runtime.nodes._base import node
from backend.runtime.state import PipelineState


@node("formatter")
def formatter_node(state: PipelineState) -> Dict[str, Any]:
    draft = state.get("draft", {})
    cited = draft.get("cited") or {}
    # cited draft (Phase 0) exposes section text under "cited_draft"; fall back to raw sections
    sections = cited.get("cited_draft") if isinstance(cited, dict) else None
    if not sections:
        sections = draft.get("sections", {})

    body_parts = []
    for name, text in (sections or {}).items():
        title = name.replace("_", " ").title()
        body_parts.append(f"## {title}\n\n{text}")
    markdown = "\n\n".join(body_parts)

    final_document = {
        "output_type": state.get("output_type", "research_paper"),
        "target_venue": state.get("target_venue", "IEEE"),
        "sections": sections,
        "references": cited.get("references", []) if isinstance(cited, dict) else [],
        "markdown": markdown,
        "review": state.get("review", {}),
        "_stub": True,  # replaced in Phase 6
    }
    return {"final_document": final_document, "status": "completed"}
