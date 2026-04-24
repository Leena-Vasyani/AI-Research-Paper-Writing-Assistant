# Retrieval Agent

## Module

- backend/core_agents/retrieval_agent.py

## What does it do?

Retrieval Agent gathers candidate papers from multiple scholarly sources and returns a normalized, deduplicated, ranked paper list suitable for synthesis and drafting.

## How does it work?

- Accepts keyword list from query stage or manual input.
- Executes parallel-like source retrieval logic against:
  - arXiv
  - OpenAlex
  - Semantic Scholar
- Normalizes each source record into a shared paper schema.
- Scores relevance using keyword overlap and metadata quality.
- Deduplicates by title/similarity and applies quality filters.

## Technologies used

- Python requests/http clients
- Source-specific API parsers
- Ranking and dedup heuristics

## Inputs and outputs

- Input:
  - keywords: list[str]
  - max_results (optional)
- Output:
  - papers: list[{title, abstract, authors, year, venue, url, score, source}]

## API dependency

- Exposed through /api/retrieve

## Failure modes and guardrails

- Source-level failures are isolated so one failing provider does not fully block retrieval.
- Applies fallback behavior when source responses are sparse or inconsistent.

## Performance notes

- Dominated by external API latency.
- Throughput depends on source rate limits and response quality.

## Extension ideas

- Add caching layer for repeated keyword sets.
- Add semantic reranking with cross-encoder for higher precision.
