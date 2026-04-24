# Smart Drafter Feature

## What does it do?

Smart Drafter is an AI-assisted writing studio for research text refinement. It combines editing, autocomplete, spelling assistance, citation workflows, table insertion, equation insertion, and export.

## How does it work?

- Uses TipTap editor with custom extensions and live text synchronization.
- Runs debounce-based autocomplete from backend.
- Computes local misspelling candidates from dictionary index.
- Supports refinement actions:
  - expand
  - academic
  - refine
  - anti_plagiarism
- Integrates citation suggestion and insertion into selected claims.

## Technologies used

- Next.js client page: web/src/app/smart-drafter/page.tsx
- TipTap ecosystem (StarterKit and extensions)
- ProseMirror decorations for spell highlighting
- Custom components:
  - CitationManager
  - EquationEditor
  - TableInsertDialog
- docx package for export capability

## Inputs and outputs

- Inputs:
  - freeform draft text
  - selected claim text
  - citations metadata
- Outputs:
  - refined text blocks
  - citation candidates and inserted markers
  - export-ready content

## API dependencies

- /api/autocomplete
- /api/refine-block
- /api/citation/suggest

## Failure modes and guardrails

- Falls back to local autocomplete if backend fails.
- Anti-plagiarism mode optionally includes source texts to reduce overlap.
- Status banners expose provider and overlap warnings when available.

## Performance and scaling notes

- Continuous editor updates and spell checks can be expensive on very large documents.
- Debounced API calls reduce backend load for autocomplete.

## Extension ideas

- Add tracked changes and reviewer comments.
- Add citation quality score per paragraph.
