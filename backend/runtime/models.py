"""
Dynamic model-tier selection for the runtime.

The architecture diagrams split work between a fast "small model" (section
cues, classification, lightweight checks) and a capable "large model"
(drafting, reasoning, review). Both tiers route through the existing
provider-fallback in ``backend.core_agents.llm_provider`` (Ollama -> Groq ->
Gemini) so we keep one battle-tested code path.

Tiering is controlled by env vars (all optional):

    OLLAMA_SMALL_MODEL   small-tier Ollama model    (default: OLLAMA_MODEL)
    OLLAMA_MODEL         large-tier Ollama model     (default: llama3.2)
    GROQ_SMALL_MODEL     small-tier Groq model       (default: llama-3.1-8b-instant)
    GROQ_LARGE_MODEL     large-tier Groq model       (default: llama-3.3-70b-versatile)
    GEMINI_SMALL_MODEL   small-tier Gemini model     (default: gemini-2.0-flash-exp)
    GEMINI_LARGE_MODEL   large-tier Gemini model     (default: gemini-2.0-flash-exp)
"""

from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Iterator, Optional

try:
    from backend.core_agents.llm_provider import chat_completion as _chat_completion
except Exception:  # pragma: no cover - import guard
    _chat_completion = None  # type: ignore[assignment]

try:
    from backend.core_agents.observability import traceable
except Exception:  # pragma: no cover - tracing optional
    def traceable(*d_args, **d_kwargs):  # type: ignore[misc]
        if len(d_args) == 1 and callable(d_args[0]) and not d_kwargs:
            return d_args[0]
        def deco(fn):
            return fn
        return deco


SMALL = "small"
LARGE = "large"


def _groq_model(tier: str) -> str:
    if tier == SMALL:
        return os.getenv("GROQ_SMALL_MODEL", "llama-3.1-8b-instant")
    return os.getenv("GROQ_LARGE_MODEL", "llama-3.3-70b-versatile")


def _gemini_model(tier: str) -> str:
    if tier == SMALL:
        return os.getenv("GEMINI_SMALL_MODEL", "gemini-2.0-flash-exp")
    return os.getenv("GEMINI_LARGE_MODEL", "gemini-2.0-flash-exp")


def _ollama_model_for(tier: str) -> Optional[str]:
    if tier == SMALL:
        return os.getenv("OLLAMA_SMALL_MODEL") or None
    # large tier uses the default OLLAMA_MODEL already honored by llm_provider
    return None


@contextmanager
def _ollama_override(model: Optional[str]) -> Iterator[None]:
    """Temporarily point ``OLLAMA_MODEL`` at a tier-specific model."""
    if not model:
        yield
        return
    prev = os.environ.get("OLLAMA_MODEL")
    os.environ["OLLAMA_MODEL"] = model
    try:
        yield
    finally:
        if prev is None:
            os.environ.pop("OLLAMA_MODEL", None)
        else:
            os.environ["OLLAMA_MODEL"] = prev


@traceable(run_type="llm", name="model.complete")
def complete(
    prompt: str,
    *,
    tier: str = LARGE,
    system: Optional[str] = None,
    max_tokens: int = 800,
    temperature: float = 0.3,
    top_p: float = 0.9,
) -> Optional[str]:
    """Run a chat completion at the requested model tier.

    Returns the response text, or ``None`` if no provider is available/responds.
    """
    if _chat_completion is None:
        return None
    with _ollama_override(_ollama_model_for(tier)):
        return _chat_completion(
            prompt,
            system=system,
            max_tokens=max_tokens,
            temperature=temperature,
            top_p=top_p,
            groq_model=_groq_model(tier),
            gemini_model=_gemini_model(tier),
        )


def small_model(prompt: str, **kwargs) -> Optional[str]:
    """Fast tier — cues, classification, lightweight checks."""
    kwargs.setdefault("max_tokens", 400)
    return complete(prompt, tier=SMALL, **kwargs)


def large_model(prompt: str, **kwargs) -> Optional[str]:
    """Capable tier — drafting, reasoning, review."""
    kwargs.setdefault("max_tokens", 1200)
    return complete(prompt, tier=LARGE, **kwargs)
