# Workflow Feature

## What does it do?

Workflow provides the guided end-to-end academic pipeline:

1. Topic analysis
2. Paper retrieval
3. Multi-paper summarization
4. Draft generation
5. Plagiarism analysis

It is the primary orchestrated feature for users who want the complete chain in one place.

## How does it work?

- Uses a step shell abstraction with completion-aware rendering.
- Tracks progression state with step IDs and unlock logic.
- Calls backend in sequence:
  - /api/query
  - /api/retrieve
  - /api/summarize
  - /api/draft
  - /api/plagiarism
- Supports keyword management, JSON export, and citation suggestion actions during flow.

## Technologies used

- Next.js client page: web/src/app/workflow/page.tsx
- Shared UI components:
  - PageHeader
  - SectionCard
  - StatCard
  - Badge
- API client: web/src/lib/api.ts
- Typed contracts: web/src/lib/types.ts

## Inputs and outputs

- Inputs:
  - research topic
  - keyword settings
  - max papers
- Outputs:
  - query keywords/subtopics
  - retrieved paper list
  - comprehensive summary object
  - draft sections
  - plagiarism report

## API dependencies

- Health check: /api/health
- Main chain endpoints listed above
- Optional citation helper: /api/citation/suggest

## Failure modes and guardrails

- Per-step error handling with retained prior outputs.
- Step-level loading status to avoid accidental double-submit.
- User can export intermediate JSON for recovery.

## Performance and scaling notes

- Most expensive operations are retrieval and summarization.
- Draft and plagiarism complexity scales with text size and paper count.

## Extension ideas

- Add checkpoint persistence to resume long workflows.
- Add branch mode to compare multiple retrieval strategies side-by-side.
