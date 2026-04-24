# Pseudocode Agent

## Module

- backend/core_agents/pseudocode_agent.py

## What does it do?

Pseudocode Agent converts source code into polished algorithm2e LaTeX pseudocode suitable for inclusion in research papers.

## How does it work?

- Uses a highly constrained system prompt with academic style rules.
- Enforces notation mapping such as assignment arrows and math-friendly symbols.
- Requires output to be raw LaTeX only, without markdown wrappers.
- Provider fallback chain:
  - Ollama via shared llm_provider
  - Gemini
  - Groq

## Technologies used

- google.generativeai SDK
- groq SDK
- shared llm_provider

## Inputs and outputs

- Input:
  - code (required)
  - algorithm_name (optional metadata)
- Output:
  - latex_code
  - provider
  - success/error status

## API dependency

- Exposed through /api/pseudocode/convert

## Failure modes and guardrails

- Rejects empty code payload.
- Cleans fenced code responses before returning.
- Provides explicit error if all providers fail.

## Performance notes

- Longer code inputs require more tokens and increase latency.

## Extension ideas

- Add language-aware parsing pass to improve abstraction quality.
- Add optional pseudocode density levels (concise, standard, verbose).
