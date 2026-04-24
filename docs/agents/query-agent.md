# Query Agent

## Module

- backend/core_agents/query_agent.py

## What does it do?

Query Agent converts a user research topic into an expanded, retrieval-ready keyword package. It creates focused search terms, subtopics, and context-aware keyword variations that downstream retrieval can use.

## How does it work?

- Uses transformer-based language understanding (SciBERT family in project context) to interpret topic semantics.
- Uses keyword extraction strategy (including KeyBERT-style flow) to surface dense terms.
- Applies fallback extraction when model outputs are weak.
- Produces ranked keyword sets and optional complexity metadata.

## Technologies used

- Python NLP stack
- Transformer embedding models
- Keyword extraction heuristics

## Inputs and outputs

- Input:
  - research_topic: string
- Output:
  - keywords: list[str]
  - optional subtopics
  - optional complexity or confidence metadata

## API dependency

- Exposed through /api/query

## Failure modes and guardrails

- Handles empty/low-signal topics with fallback keyword generation.
- Avoids returning unusable empty results when possible.

## Performance notes

- Computation is moderate compared to retrieval/summarization.
- Cost is mostly model inference on short text.

## Extension ideas

- Add domain packs (biomedical, cybersecurity, NLP) with tuned stopword sets.
- Add multilingual query decomposition.
