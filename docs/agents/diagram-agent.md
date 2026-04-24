# Diagram Agent

## Module

- backend/core_agents/diagram_agent.py

## What does it do?

Diagram Agent converts textual descriptions into valid Mermaid diagrams. It supports multiple diagram families and returns code suitable for direct renderer consumption.

## How does it work?

- Builds a strict prompt with Mermaid-only output instruction.
- Accepts an optional diagram_type hint to guide structure.
- Provider fallback chain:
  - Ollama via shared llm_provider
  - Gemini
  - Groq
- Strips markdown fences and normalizes final Mermaid content.

## Technologies used

- google genai client
- groq client
- shared llm_provider utility

## Inputs and outputs

- Input:
  - description (required)
  - diagram_type (optional)
- Output:
  - success flag
  - mermaid_code
  - provider metadata

## API dependency

- Exposed through /api/diagram/generate

## Failure modes and guardrails

- Returns structured error when all providers fail.
- Handles fenced response formatting from providers.

## Performance notes

- Runtime is mostly provider-bound.

## Extension ideas

- Add Mermaid syntax lint pass before returning output.
- Add architecture-aware templates for cloud, microservices, and ML pipelines.
