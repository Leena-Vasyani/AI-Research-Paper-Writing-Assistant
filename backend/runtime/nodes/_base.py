"""
Shared infrastructure for pipeline nodes.

- Lazy, cached singletons for the heavy agent classes (models load on first use).
- A ``@node(stage)`` decorator that standardizes status updates, timing, and
  error capture so individual node bodies stay focused on agent orchestration.
"""

from __future__ import annotations

import logging
import time
from functools import lru_cache, wraps
from typing import Any, Callable, Dict

from backend.runtime.state import PipelineState, mark_timing

logger = logging.getLogger("runtime.nodes")

NodeFn = Callable[[PipelineState], Dict[str, Any]]


def node(stage: str) -> Callable[[NodeFn], NodeFn]:
    """Wrap a node body with status/timing/error handling.

    The body returns a partial-state dict of keys to merge. Exceptions are
    captured into ``errors``/``warnings`` (additive reducers) instead of
    crashing the graph, so a single failing stage degrades gracefully.
    """

    def decorator(fn: NodeFn) -> NodeFn:
        @wraps(fn)
        def wrapper(state: PipelineState) -> Dict[str, Any]:
            started = time.time()
            update: Dict[str, Any] = {"status": stage}
            try:
                logger.info("[%s] start", stage)
                result = fn(state) or {}
                update.update(result)
                logger.info("[%s] done", stage)
            except Exception as exc:  # noqa: BLE001 - graph must not crash on one node
                logger.exception("[%s] failed", stage)
                update["errors"] = [{"stage": stage, "error": f"{type(exc).__name__}: {exc}"}]
                update["warnings"] = [f"{stage} failed: {exc}"]
            update["stage_timings"] = mark_timing(state, stage, started)
            return update

        return wrapper

    return decorator


# ---------------------------------------------------------------------------
# Lazy agent singletons (heavy imports / model loads deferred to first use)
# ---------------------------------------------------------------------------


@lru_cache(maxsize=1)
def keyword_agent():
    from backend.core_agents.keyword_agent import KeywordExtractionAgent
    return KeywordExtractionAgent()


@lru_cache(maxsize=1)
def query_agent():
    from backend.core_agents.query_agent import ScientificQueryAgent
    return ScientificQueryAgent()


@lru_cache(maxsize=1)
def search_agent():
    from backend.core_agents.search_agent import SearchAgent
    return SearchAgent(keyword_agent=keyword_agent())


@lru_cache(maxsize=1)
def topic_mining_agent():
    from backend.core_agents.topic_mining_agent import TopicMiningAgent
    return TopicMiningAgent()


@lru_cache(maxsize=1)
def summarization_agent():
    from backend.core_agents.summarization_agent import PaperSummarizationAgent
    return PaperSummarizationAgent()


@lru_cache(maxsize=1)
def drafting_agent():
    from backend.fine_tuning.fine_tuned_drafting_agent import get_drafting_agent, DraftingConfig
    return get_drafting_agent(DraftingConfig())


@lru_cache(maxsize=1)
def plagiarism_agent():
    from backend.core_agents.plagiarism_agent import PlagiarismDetectionAgent
    return PlagiarismDetectionAgent()


@lru_cache(maxsize=1)
def citation_agent():
    from backend.core_agents.citation_agent import CitationAgent
    return CitationAgent()
