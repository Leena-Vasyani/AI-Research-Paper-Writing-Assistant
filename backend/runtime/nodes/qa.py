"""
Q&A node — derive research-level questions and grounded answers from the corpus.

Runs between Topic Mining and Outline so it can use the mined themes/gaps, and
so its Q&A pairs are available to the Drafting node (which injects them into the
Introduction and Related-Work sections). Delegates to the QAAgent, which
degrades gracefully to a deterministic, gap-oriented heuristic when no LLM is
available.
"""

from __future__ import annotations

from typing import Any, Dict

from backend.runtime.nodes._base import node, qa_agent
from backend.runtime.state import PipelineState


@node("qa")
def qa_node(state: PipelineState) -> Dict[str, Any]:
    result = qa_agent().generate(
        state["topic"],
        state.get("corpus", []),
        themes=state.get("themes", {}),
        constraints=state.get("constraints", {}),
    )
    return {"qa": result}
