# Agent Hub Feature

## What does it do?

Agent Hub is the independent execution surface for backend agents. Unlike Workflow, it does not force a sequence. Users can run query, retrieval, summary, draft, and plagiarism checks in any order.

## How does it work?

- Maintains editable state for each artifact as JSON or generated output.
- Supports direct document upload and text extraction to seed downstream steps.
- Includes quick-start actions that bypass strict dependencies by auto-seeding missing inputs.
- Includes focus-view filtering so users can isolate one agent panel.

## Technologies used

- Next.js client page: web/src/app/agent-hub/page.tsx
- UI components:
  - PageHeader
  - SectionCard
  - StatCard
  - Badge
- API layer: web/src/lib/api.ts
- Type layer: web/src/lib/types.ts

## Inputs and outputs

- Inputs:
  - topic text
  - optional uploaded file
  - optional JSON payloads for papers, summaries, drafts, sources
- Outputs:
  - per-agent structured objects with export support

## API dependencies

- /api/extract-text
- /api/query
- /api/retrieve
- /api/summarize
- /api/draft
- /api/plagiarism

## Failure modes and guardrails

- JSON parsing guards for manual payload edits.
- Auto-fallback seed paths from uploaded document text.
- Action-level error messaging without clearing all state.

## Performance and scaling notes

- Flexible mode can trigger heavy calls without sequence gating, so users can overload operations more easily than Workflow.
- Statistics panel provides quick health awareness of active state size.

## Extension ideas

- Add saved agent presets (for domain-specific runs).
- Add one-click replay from a stored state snapshot.
