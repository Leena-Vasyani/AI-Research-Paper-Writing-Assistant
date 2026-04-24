# Universal Research Formatter Feature

## What does it do?

Universal Research Formatter converts and edits research content into publication templates such as IEEE, ACM SIGCONF, Springer LNCS, APA, and MLA. It provides a live page-layout editing experience with explicit typography and margin controls.

## How does it work?

- Maintains format presets with family-level metadata.
- Renders content through a TipTap editor configured for academic structures.
- Applies format-specific transformations via frontend formatters.
- Supports AI quick-fix commands for layout changes.
- Supports equation and table insertion in an interactive editing pipeline.

## Technologies used

- Next.js client page: web/src/app/universal-research-formatter/page.tsx
- TipTap and related extensions:
  - table extensions
  - text align
  - underline/subscript/superscript
- Formatting libraries in web/src/lib/formatters
- Parsing helpers in web/src/lib/parser

## Inputs and outputs

- Inputs:
  - raw or imported text/documents
  - selected format preset
  - style parameters (font, margins, columns)
- Outputs:
  - formatted editor content
  - exportable format artifacts

## API dependencies

- /api/format-commands
- /api/format-ieee
- /api/compile-pdf

## Failure modes and guardrails

- Preset defaults ensure valid formatting even with partial user input.
- Backend command failure does not block manual formatting operations.
- Export and compilation paths surface detailed error logs.

## Performance and scaling notes

- Rich editor with large content and many tables/equations can increase render cost.
- PDF compilation latency depends on LaTeX availability and input complexity.

## Extension ideas

- Add side-by-side diff between source and formatted output.
- Add publisher-specific validation checklist before export.
