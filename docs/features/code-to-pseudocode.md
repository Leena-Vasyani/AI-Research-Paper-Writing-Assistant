# Code-to-Pseudocode Feature

## What does it do?

Code-to-Pseudocode transforms implementation code into publication-grade LaTeX pseudocode, optimized for algorithm2e style used in academic papers.

## How does it work?

- Accepts source code in multiple languages.
- Applies strict system instructions for algorithm abstraction.
- Enforces notation conventions (assignment arrows, mathematical symbols).
- Returns clean LaTeX body without explanatory prose.

## Technologies used

- Next.js page: web/src/app/code-to-pseudocode/page.tsx
- Backend converter: backend/core_agents/pseudocode_agent.py
- LLM provider fallback chain for robust generation

## Inputs and outputs

- Inputs:
  - code snippet
  - optional algorithm name
- Outputs:
  - algorithm2e-compatible LaTeX pseudocode
  - provider metadata

## API dependencies

- /api/pseudocode/convert

## Failure modes and guardrails

- Empty input is rejected early.
- Markdown fences are stripped if provider adds them.
- Returns structured error if generation fails across providers.

## Performance and scaling notes

- Runtime scales with code length and complexity.
- Very long files should be segmented for better quality.

## Extension ideas

- Add language-specific pre-parsing for cleaner semantic extraction.
- Add optional style modes (algorithmicx, plain text pseudocode).
