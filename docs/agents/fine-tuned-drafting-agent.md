# Fine-Tuned Drafting Agent

## Module

- backend/fine_tuning/fine_tuned_drafting_agent.py

## What does it do?

FineTunedDraftingAgent generates and cleans academic draft sections. It wraps model loading, generation configuration, and post-generation sanitization to improve final writing quality.

## How does it work?

- Loads base/fine-tuned sequence-to-sequence model and tokenizer.
- Generates section text using configurable decoding parameters.
- Runs ContentCleaner pipeline:
  - remove publishing/legal metadata artifacts
  - remove instruction leakage
  - fix incomplete or cut-off sentence patterns
  - clean malformed numbered lists
- Validates generated content for minimal quality and topic relevance.

## Technologies used

- PyTorch
- Hugging Face seq2seq models and pipelines
- regex-based cleaning/validation layer

## Inputs and outputs

- Inputs:
  - prompt/topic/section controls depending on call site
- Outputs:
  - cleaned section text
  - quality flags/issues where relevant

## API dependency

Used by drafting flows behind /api/draft and related refinement paths depending on wiring.

## Failure modes and guardrails

- Cleans non-academic artifacts that frequently appear in raw model output.
- Validates short/off-topic outputs and reports issues.

## Performance notes

- Generation time depends on token budgets and beam settings.
- Cleaner is lightweight relative to model inference.

## Extension ideas

- Add section-specific decoding profiles.
- Add constrained decoding with style lexicons.
