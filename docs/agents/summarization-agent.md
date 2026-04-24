# Summarization Agent

## Module

- backend/core_agents/summarization_agent.py

## What does it do?

Summarization Agent transforms a list of retrieved papers into a structured, comparative summary package used by drafting and analysis stages.

## How does it work?

- Ingests paper abstracts/full texts where available.
- Builds section-level synthesis (problem, methods, findings, limitations).
- Uses transformer summarization and provider-backed generation fallback.
- Extracts evidence-like statements and alignment to keyword intent.
- Produces concise and full summary variants plus confidence metadata.

## Technologies used

- Hugging Face transformers summarization pipeline
- Shared LLM provider fallback chain
- Text cleaning and section synthesis heuristics

## Inputs and outputs

- Input:
  - papers: list[paper]
  - keywords: list[str]
- Output:
  - comprehensive summary object with sections and evidence

## API dependency

- Exposed through /api/summarize

## Failure modes and guardrails

- Handles variable paper quality and missing abstracts.
- Falls back across providers if preferred model path fails.
- Keeps structured output contract even under partial signal.

## Performance notes

- One of the heavier modules because it combines multi-document processing and generation.

## Extension ideas

- Add contradiction detection across papers.
- Add claim-level citation anchors for downstream drafting.
