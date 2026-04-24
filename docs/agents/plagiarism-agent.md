# Plagiarism Agent

## Module

- backend/core_agents/plagiarism_agent.py

## What does it do?

Plagiarism Agent estimates semantic overlap between generated draft sections and source papers to detect potential originality risks before export/submission.

## How does it work?

- Splits generated draft into sentence-level units.
- Compares draft units with source text embeddings/similarity scoring.
- Aggregates overlap into section and global risk metrics.
- Returns flagged snippets and interpretable score summaries.

## Technologies used

- Sentence-transformers style embeddings
- Similarity metrics (cosine-style semantic overlap)
- Section-aware reporting logic

## Inputs and outputs

- Input:
  - generated_draft
  - source_papers
  - research_topic
- Output:
  - plagiarism report with overall score, section scores, and flags

## API dependency

- Exposed through /api/plagiarism

## Failure modes and guardrails

- Handles missing source abstracts with degraded but valid scoring path.
- Avoids binary pass/fail framing; reports confidence-aware overlap.

## Performance notes

- Complexity grows with sentence count times source corpus size.

## Extension ideas

- Add per-claim rewrite suggestions for high-overlap segments.
- Add configurable threshold profiles by institution policy.
