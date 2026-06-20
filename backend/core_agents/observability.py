"""
LangSmith observability — guarded tracing helpers.

Provides a ``@traceable`` decorator that is a genuine LangSmith trace span when
``langsmith`` is installed AND tracing is enabled (a key is present), and a
zero-overhead no-op otherwise. Also normalizes env aliases so either the
``LANGSMITH_*`` or ``LANGCHAIN_*`` variable names work.

Usage:
    from backend.core_agents.observability import traceable

    @traceable(run_type="llm", name="chat_completion")
    def chat_completion(...): ...

LangGraph emits node/edge spans automatically once ``LANGCHAIN_TRACING_V2`` and
an API key are set; this module adds the LLM-level spans that our raw provider
calls would otherwise miss.
"""

from __future__ import annotations

import logging
import os

logger = logging.getLogger("observability")

try:  # optional dependency
    from langsmith import traceable as _ls_traceable
    _HAS_LANGSMITH = True
except Exception:  # pragma: no cover - optional
    _ls_traceable = None
    _HAS_LANGSMITH = False


def tracing_enabled() -> bool:
    """True only if langsmith is importable and tracing is switched on."""
    return _HAS_LANGSMITH and os.getenv("LANGCHAIN_TRACING_V2", "").strip().lower() in (
        "1",
        "true",
        "yes",
    )


def _wrap(fn, args=(), kwargs=None):
    kwargs = kwargs or {}
    # Decide once, at decoration time (init_tracing runs before agent imports).
    if _HAS_LANGSMITH and tracing_enabled():
        try:
            return _ls_traceable(*args, **kwargs)(fn)
        except Exception:  # pragma: no cover - never break the app for tracing
            return fn
    return fn


def traceable(*d_args, **d_kwargs):
    """Drop-in for ``langsmith.traceable`` that no-ops when tracing is off.

    Supports both bare ``@traceable`` and parametrized ``@traceable(name=...)``.
    """
    # Bare usage: @traceable
    if len(d_args) == 1 and callable(d_args[0]) and not d_kwargs:
        return _wrap(d_args[0])

    # Parametrized usage: @traceable(run_type="llm", name="...")
    def deco(fn):
        return _wrap(fn, d_args, d_kwargs)

    return deco


def init_tracing() -> bool:
    """Normalize env aliases and enable tracing when an API key is present.

    - ``LANGSMITH_API_KEY`` -> ``LANGCHAIN_API_KEY`` (and project alias)
    - default project ``researchgen``
    - turn on ``LANGCHAIN_TRACING_V2`` only when a key exists and the user
      hasn't explicitly set it.

    Returns whether tracing ended up enabled.
    """
    if not os.getenv("LANGCHAIN_API_KEY") and os.getenv("LANGSMITH_API_KEY"):
        os.environ["LANGCHAIN_API_KEY"] = os.environ["LANGSMITH_API_KEY"]

    if not os.getenv("LANGCHAIN_PROJECT"):
        os.environ["LANGCHAIN_PROJECT"] = os.getenv("LANGSMITH_PROJECT", "researchgen")

    key = os.getenv("LANGCHAIN_API_KEY", "").strip()
    if key and os.getenv("LANGCHAIN_TRACING_V2", "").strip() == "":
        os.environ["LANGCHAIN_TRACING_V2"] = "true"

    enabled = tracing_enabled()
    if enabled:
        logger.info(
            "LangSmith tracing enabled (project=%s)", os.getenv("LANGCHAIN_PROJECT")
        )
    elif key and not _HAS_LANGSMITH:
        logger.warning("LANGSMITH key set but 'langsmith' not installed; tracing off.")
    return enabled
