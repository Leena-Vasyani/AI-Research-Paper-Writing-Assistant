# LLM Provider Utility

## Module

- backend/core_agents/llm_provider.py

## What does it do?

This module centralizes provider selection and fallback for text generation. It provides one shared chat_completion interface used by multiple agents.

## How does it work?

Provider priority is explicit:

1. Ollama (cloud native endpoint or OpenAI-compatible self-hosted)
2. Groq
3. Gemini

- Builds message payload with optional system prompt.
- Tries each provider in order.
- Returns first successful non-empty response.
- Logs provider outcomes for debugging.

## Technologies used

- openai client (for OpenAI-compatible Ollama mode)
- requests (for native Ollama cloud chat endpoint)
- groq SDK
- google genai SDK

## Inputs and outputs

- Input:
  - prompt
  - system (optional)
  - generation parameters (max_tokens, temperature, top_p)
- Output:
  - response text or None

## Environment variables

- OLLAMA_BASE_URL
- OLLAMA_MODEL
- OLLAMA_API_KEY
- GROQ_API_KEY
- GEMINI_API_KEY

## Failure modes and guardrails

- Optional imports prevent startup failures when one SDK is missing.
- Each provider call is wrapped and failure-isolated.
- Returns None only after all providers fail.

## Performance notes

- Provider latency dominates runtime.
- Proper provider ordering minimizes average wait time in healthy setups.

## Extension ideas

- Add retries with exponential backoff.
- Add circuit breaker to temporarily skip unstable provider.
