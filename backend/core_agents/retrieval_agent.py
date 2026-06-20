"""
Backwards-compatibility shim.

The retrieval agent was reworked and renamed to the Search Agent in Phase 1 of
the multi-agent pipeline migration. This module re-exports the new home so
legacy imports (``from core_agents.retrieval_agent import PaperRetrievalAgent``)
keep working until callers are migrated to ``search_agent``.
"""

from backend.core_agents.search_agent import (  # noqa: F401
    SearchAgent,
    PaperRetrievalAgent,
    CitationGraph,
    _classify_domain,
)

__all__ = ["SearchAgent", "PaperRetrievalAgent", "CitationGraph", "_classify_domain"]
