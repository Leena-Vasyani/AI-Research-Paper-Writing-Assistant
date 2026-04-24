# Citation Agent

## Module

- backend/core_agents/citation_agent.py

## What does it do?

Citation Agent identifies claims that require support and suggests ranked citation candidates from available source papers in selected output style.

## How does it work?

- Detects citation-worthy segments in draft text.
- Scores source papers for claim relevance and confidence.
- Applies thresholding and ranking to avoid low-quality suggestions.
- Formats output references in style-compatible patterns.

## Technologies used

- Text matching and relevance scoring heuristics
- Style formatter logic (IEEE and related)
- Confidence filtering and fallback strategy

## Inputs and outputs

- Input:
  - text or claim snippet
  - source papers
  - citation style
- Output:
  - ranked suggestions with confidence and formatted citation text

## API dependency

- Exposed through /api/citation/suggest and /api/citation/format

## Failure modes and guardrails

- Provides graceful fallback when strict thresholds produce no suggestions.
- Maintains low-confidence signaling for transparent UX.

## Performance notes

- Lightweight compared to summarization and RAG.

## Extension ideas

- Add claim type detection (factual, comparative, historical) to improve citation matching.
- Add source trust weighting by venue quality.
