# Diagram Generator Feature

## What does it do?

Diagram Generator converts natural language architecture/process descriptions into Mermaid diagram code for direct embedding in documents and presentations.

## How does it work?

- Accepts freeform text description and optional diagram-type hint.
- Constructs strict prompt instructions for valid Mermaid output only.
- Tries provider chain in order to maximize reliability.
- Normalizes fenced code output into raw Mermaid body.

## Technologies used

- Next.js page: web/src/app/diagram-generator/page.tsx
- Backend agent: backend/core_agents/diagram_agent.py
- Mermaid rendering component: web/src/components/Mermaid.tsx
- Provider fallback chain via Ollama/Gemini/Groq

## Inputs and outputs

- Inputs:
  - textual process or architecture description
  - optional type hint (flowchart, sequence, ER, etc.)
- Outputs:
  - Mermaid code
  - provider metadata

## API dependencies

- /api/diagram/generate

## Failure modes and guardrails

- Rejects empty descriptions.
- Returns structured failure when all providers fail.
- Cleans markdown fences to avoid renderer errors.

## Performance and scaling notes

- Generation latency primarily depends on LLM response time.
- Diagram rendering complexity depends on Mermaid graph size.

## Extension ideas

- Add syntax validator with auto-fix suggestions.
- Add template library for common software architectures.
