# Summary Quality Check Utility

## Module

- backend/core_agents/summary_quality_check.py

## What does it do?

This utility is a diagnostic runner for summarization quality across providers. It is primarily used for manual verification and provider comparison.

## How does it work?

- Defines a sample text and keyword list.
- Instantiates PaperSummarizationAgent.
- Iterates over providers (groq, gemini, local).
- Skips unavailable providers based on configured keys/clients.
- Prints resulting summaries for quick quality inspection.

## Technologies used

- core summarization agent
- provider availability checks

## Inputs and outputs

- Input:
  - internal sample text and static keyword list
- Output:
  - console summaries by provider

## API dependency

None. This is script-like local validation code.

## Failure modes and guardrails

- Provider checks prevent hard failure when keys are missing.
- Intended for local quality benchmarking, not production serving.

## Performance notes

- Runtime depends on provider response latency.

## Extension ideas

- Add automated scoring and JSON report output.
- Integrate into CI as optional quality smoke test.
