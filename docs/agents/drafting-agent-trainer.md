# Drafting Agent Trainer

## Module

- backend/fine_tuning/drafting_agent_trainer.py

## What does it do?

Drafting Agent Trainer prepares and fine-tunes a language model to generate original academic writing by learning patterns from collected summaries and drafted outputs.

## How does it work?

- Dataset creation:
  - extracts academic discourse patterns (transitions, phrasing, argument flow)
  - builds prompt-target pairs for abstract, introduction, and related work
- Model setup:
  - loads base model/tokenizer
  - configures LoRA/PEFT parameters for efficient adaptation
- Training loop:
  - tokenizes examples
  - uses Hugging Face Trainer with configurable training arguments
  - persists checkpoints and final adapted model artifacts

## Technologies used

- PyTorch
- Hugging Face transformers and datasets
- PEFT/LoRA
- tqdm and numpy for processing utilities

## Inputs and outputs

- Inputs:
  - training data from TrainingDataManager
  - base model identifier
  - training hyperparameters
- Outputs:
  - fine-tuned model artifacts
  - training logs/metrics

## API dependency

Typically offline/training-only and not called in the standard online request path.

## Failure modes and guardrails

- Skips empty/invalid project samples.
- Uses pattern-driven prompts to reduce direct text copying risk.

## Performance notes

- GPU strongly recommended for practical training throughput.
- Resource usage depends on model size and sequence lengths.

## Extension ideas

- Add evaluation harness with academic quality metrics.
- Add curriculum schedule by domain complexity.
