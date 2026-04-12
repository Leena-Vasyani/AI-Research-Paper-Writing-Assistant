"""
Shared LLM provider utility.

Priority: Ollama Cloud (qwen3.5:397b-cloud) → Groq → Gemini → None

Ollama exposes an OpenAI-compatible REST API at:
  http://localhost:11434/v1   (default local)
  or OLLAMA_BASE_URL env var  (cloud / custom)

Set in .env:
  OLLAMA_BASE_URL=<your ollama cloud base url>  # e.g. https://api.example.com/v1
  OLLAMA_MODEL=qwen3.5:397b-cloud               # model tag
"""

from __future__ import annotations

import os
import json
import requests as _requests
from typing import List, Optional

# ---------------------------------------------------------------------------
# Lazy imports — keep hard deps optional so startup never crashes
# ---------------------------------------------------------------------------

try:
    from openai import OpenAI as _OpenAIClient   # used for Ollama OpenAI-compat API
except ImportError:
    _OpenAIClient = None  # type: ignore[assignment]

try:
    from groq import Groq as _GroqClient
except ImportError:
    _GroqClient = None  # type: ignore[assignment]

try:
    from google import genai as _genai
except ImportError:
    _genai = None  # type: ignore[assignment]

# ---------------------------------------------------------------------------
# Config helpers
# ---------------------------------------------------------------------------

def _ollama_base_url() -> str:
    return os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1").rstrip("/")

def _ollama_model() -> str:
    return os.getenv("OLLAMA_MODEL", "qwen3.5:397b-cloud")

def _groq_api_key() -> str:
    return os.getenv("GROQ_API_KEY", "").strip()

def _gemini_api_key() -> str:
    return os.getenv("GEMINI_API_KEY", "").strip()

# ---------------------------------------------------------------------------
# Individual provider callers
# ---------------------------------------------------------------------------

def _ollama_api_key() -> str:
    """Some Ollama Cloud deployments require an API key."""
    return os.getenv("OLLAMA_API_KEY", "ollama").strip() or "ollama"


def _call_ollama(
    messages: List[dict],
    max_tokens: int = 400,
    temperature: float = 0.3,
    top_p: float = 0.9,
) -> Optional[str]:
    """
    Call Ollama.
    - If base URL contains 'ollama.com': uses Ollama's native /api/chat endpoint.
    - Otherwise: uses OpenAI-compatible /v1/chat/completions (for self-hosted).
    """
    base_url = _ollama_base_url()
    model = _ollama_model()
    api_key = _ollama_api_key()

    # ---- Native Ollama Cloud (ollama.com/api) ----
    if "ollama.com" in base_url:
        try:
            url = base_url.rstrip("/") + "/chat"
            payload = {
                "model": model,
                "messages": messages,
                "stream": False,
                "options": {
                    "temperature": temperature,
                    "top_p": top_p,
                },
            }
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
            }
            resp = _requests.post(url, json=payload, headers=headers, timeout=120)
            resp.raise_for_status()
            data = resp.json()
            content = data.get("message", {}).get("content", "")
            if not content.strip():
                print(f"   [!] Ollama Cloud returned empty content. Dumping to ollama_debug.json")
                with open("ollama_debug.json", "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2)
            return content.strip() if content else None
        except Exception as exc:
            print(f"   [ERROR] Ollama Cloud FAILED -> {type(exc).__name__}: {exc}")
            print(f"      URL: {base_url}  |  Model: {model}")
            return None

    # ---- Self-hosted Ollama (OpenAI-compatible /v1) ----
    if _OpenAIClient is None:
        print("   ⚠️ Ollama skipped: openai package not installed (pip install openai)")
        return None
    try:
        client = _OpenAIClient(
            api_key=api_key,
            base_url=base_url,
        )
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            top_p=top_p,
            max_tokens=max_tokens,
        )
        content = response.choices[0].message.content
        return content.strip() if content else None
    except Exception as exc:
        print(f"   [ERROR] Ollama (self-hosted) FAILED -> {type(exc).__name__}: {exc}")
        print(f"      URL: {base_url}  |  Model: {model}")
        return None


def _call_groq(
    messages: List[dict],
    max_tokens: int = 400,
    temperature: float = 0.3,
    top_p: float = 0.9,
    model: str = "llama-3.3-70b-versatile",
) -> Optional[str]:
    """Call Groq."""
    api_key = _groq_api_key()
    if not api_key or _GroqClient is None:
        return None
    try:
        client = _GroqClient(api_key=api_key)
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            top_p=top_p,
            max_tokens=max_tokens,
        )
        content = response.choices[0].message.content
        return content.strip() if content else None
    except Exception as exc:
        print(f"   ⚠️ Groq call failed: {exc}")
        return None


def _call_gemini(
    prompt: str,
    system: Optional[str] = None, # Add system as a parameter here
    max_tokens: int = 400,
    temperature: float = 0.3,
    top_p: float = 0.9,
    model: str = "gemini-2.0-flash-exp",
) -> Optional[str]:
    api_key = _gemini_api_key()
    if not api_key or _genai is None:
        return None
    try:
        client = _genai.Client(api_key=api_key)
        
        # Build the config dictionary
        config_dict = {
            "temperature": temperature,
            "top_p": top_p,
            "max_output_tokens": max_tokens,
        }
        
        # Inject system instruction if provided
        if system:
            config_dict["system_instruction"] = system

        response = client.models.generate_content(
            model=model,
            contents=prompt,
            config=config_dict,
        )
        return response.text.strip() if response and response.text else None
    except Exception as exc:
        print(f"  ⚠️ Gemini call failed: {exc}")
        return None

# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

def chat_completion(
    prompt: str,
    *,
    system: Optional[str] = None,
    max_tokens: int = 400,
    temperature: float = 0.3,
    top_p: float = 0.9,
    groq_model: str = "llama-3.3-70b-versatile",
    gemini_model: str = "gemini-2.0-flash-exp",
) -> Optional[str]:
    """
    Send a chat completion request trying providers in order:
      1. Ollama (OLLAMA_BASE_URL / OLLAMA_MODEL)
      2. Groq   (GROQ_API_KEY)
      3. Gemini (GEMINI_API_KEY)

    Returns the response text, or None if all providers fail.
    """
    messages: List[dict] = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    # 1. Ollama
    print(f"   [>>] Trying provider: ollama ({_ollama_model()})")
    result = _call_ollama(messages, max_tokens=max_tokens, temperature=temperature, top_p=top_p)
    if result:
        print("   [OK] Ollama responded")
        return result

    # 2. Groq
    print("   [>>] Trying provider: groq")
    result = _call_groq(messages, max_tokens=max_tokens, temperature=temperature, top_p=top_p, model=groq_model)
    if result:
        print("   [OK] Groq responded")
        return result

    # 3. Gemini
    print("   [>>] Trying provider: gemini")
    # For Gemini combine system + user as one prompt
    full_prompt = f"{system}\n\n{prompt}" if system else prompt
    result = _call_gemini(full_prompt, max_tokens=max_tokens, temperature=temperature, top_p=top_p, model=gemini_model)
    if result:
        print("   [OK] Gemini responded")
        return result

    print("   [!!] All LLM providers failed")
    return None


def active_providers() -> List[str]:
    """Return list of currently configured provider names (for health/debug)."""
    providers = []
    if _OpenAIClient is not None:
        providers.append(f"ollama({_ollama_model()})")
    if _groq_api_key() and _GroqClient is not None:
        providers.append("groq")
    if _gemini_api_key() and _genai is not None:
        providers.append("gemini")
    return providers
