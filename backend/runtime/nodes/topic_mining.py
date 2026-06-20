"""
Topic Mining node — cluster the retrieved corpus into themes / taxonomy / gaps.

Delegates to the TopicMiningAgent (semantic clustering with graceful fallback
to query-subtopic grouping). Output feeds the Outline node's structure planning.
"""

from __future__ import annotations

from typing import Any, Dict

from backend.runtime.nodes._base import node, topic_mining_agent
from backend.runtime.state import PipelineState


@node("topic_mining")
def topic_mining_node(state: PipelineState) -> Dict[str, Any]:
    corpus = state.get("corpus", [])
    analysis = state.get("query_analysis", {})

    themes = topic_mining_agent().mine(corpus, query_analysis=analysis)
    return {"themes": themes}
