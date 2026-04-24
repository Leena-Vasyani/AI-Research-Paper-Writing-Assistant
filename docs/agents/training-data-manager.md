# Training Data Manager

## Module

- backend/core_agents/training_data_manager.py

## What does it do?

TrainingDataManager collects completed research cycles and stores them as reusable supervision data for drafting model fine-tuning.

## How does it work?

- Loads existing JSON dataset at startup.
- Creates training samples from:
  - research topic
  - query outputs
  - high-confidence paper summaries
  - generated draft sections
- Applies quality gating:
  - requires summaries with confidence greater than threshold
  - requires minimum count of good references
- Saves data incrementally and exposes dataset statistics/export operations.

## Technologies used

- JSON file persistence
- lightweight Python data processing

## Inputs and outputs

- Input:
  - topic, query_result, paper_summaries, generated_draft
- Output:
  - appended training sample records
  - statistics and export files

## API dependency

Indirect utility consumed by fine-tuning pipeline, not typically exposed as direct API endpoint.

## Failure modes and guardrails

- Corrupt data file handling with safe empty fallback.
- Skips invalid or low-quality sample candidates.

## Performance notes

- Lightweight in normal use; storage scales linearly with sample count.

## Extension ideas

- Migrate to SQLite/Parquet for large-scale training corpora.
- Add schema versioning for backward compatibility.
