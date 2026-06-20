"""
Formatter node — assemble the final exportable artifact.

Delegates to the FormatterAgent: LaTeX + Markdown export, consolidated
references, blueprint figure/plot directives, and export-readiness from the
citation grounding gate.
"""

from __future__ import annotations

from typing import Any, Dict

from backend.runtime.nodes._base import node, formatter_agent
from backend.runtime.state import PipelineState


@node("formatter")
def formatter_node(state: PipelineState) -> Dict[str, Any]:
    draft = state.get("draft", {})
    cited = draft.get("cited") or {}

    final_document = formatter_agent().format(
        draft,
        state.get("blueprint", {}),
        citation_result=cited,
        grounding=cited.get("grounding"),
        review=state.get("review", {}),
    )
    return {"final_document": final_document, "status": "completed"}
