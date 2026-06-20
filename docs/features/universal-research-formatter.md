# Universal Research Formatter Feature

## Overview and motivation

Universal Research Formatter is a publication preparation workspace that turns raw or semi-structured research text into template-compliant layouts for IEEE, ACM SIGCONF, Springer LNCS, APA, and MLA. The goal is to collapse the gap between content drafting and final submission requirements by combining a deterministic formatting pipeline with an interactive editor and export options. Instead of relying on manual styling in word processors, the formatter encodes template rules (page size, column count, fonts, heading numbering, margins, and line spacing) as explicit presets, then applies them consistently across the document. This allows a user to paste content, normalize it, and immediately see a layout that aligns with common venue expectations.

## System architecture

The feature is implemented as a Next.js client page backed by a structured editor. TipTap is used for rich text editing, with extensions that support tables, underline, subscript, superscript, and alignment, and with custom IEEE nodes that preserve template semantics while editing. A set of format presets defines family-level metadata (IEEE, ACM, Springer, APA, MLA) and template-specific parameters such as column count, margins, and title sizing. Parsing utilities convert raw input into a structured document model, while formatter modules render that model into HTML aligned with the selected template family. API endpoints support AI layout commands and server-side PDF compilation, while local fallbacks keep editing functional when the backend is unavailable.

## Processing pipeline

1. Input ingestion: users paste or type raw text. A smart paste handler detects HTML tables on the clipboard and converts them into a pipe-delimited representation so that table structure is preserved even if the pasted content is unstructured.
2. Parsing and normalization: the parser cleans template boilerplate, detects headings (Roman or Arabic numbering, title-case cues, and common section keywords), and separates abstract, keywords, references, and appendices. Inline math is extracted before HTML escaping and converted into safe HTML entities. Citation patterns such as [1], [1,2], and [1-3] are identified and prepared for backlinking.
3. Structured model: the parser emits a normalized document model with nodes for headings, paragraphs, tables, algorithms, equations, and references. This model becomes the single source of truth for formatting.
4. Template rendering: a format-specific renderer produces HTML with template-aligned classes (for example IEEE or ACM styles). The renderer enforces numbering conventions, heading casing, column-aware layout hints, caption styles, and reference formatting. For IEEE, it can insert drop caps for journal or transactions styles; for ACM, it inserts copyright and CCS or keyword blocks.
5. Preview and page estimation: the resulting HTML is injected into the editor and stored as the preview snapshot. A page estimator computes approximate length based on column settings to give immediate feedback.

## Editing and interaction model

The editor exposes both toolbar and context menu actions for headings, emphasis, alignment, lists, tables, figures, and equations. Figures are inserted as structured blocks with caption fields and auto-incremented numbering. Equations can be inline or block-level, and are preserved through the parsing and rendering pipeline. A dedicated thesis mode provides front-matter builders (cover page, certificate, declaration, acknowledgement, table of contents, and glossary). These blocks are inserted as separate sections with explicit page breaks so the exported layout mirrors institutional report requirements.

## AI assistance and command layer

Two AI-assisted paths exist. First, the AI Enhance action calls a backend formatter endpoint to refine grammar and structure, then converts the returned HTML back into deterministic input so the strict formatter can re-apply the chosen template. Second, the Quick Fix command bar sends natural-language layout requests to the format-commands endpoint. The response contains safe CSS variable updates (column count, font size, margins) and a small set of editor actions. If the AI endpoints are unavailable, the deterministic formatter still produces a complete, editable layout.

## Export and artifacts

Export outputs are designed for submission workflows. The LaTeX exporter traverses the editor document tree and maps headings, paragraphs, lists, tables, equations, code blocks, figures, and page breaks into LaTeX constructs, then downloads a .tex artifact. For PDF export, the document is compiled server-side via the compile endpoint. If LaTeX is unavailable on the server, the system falls back to browser-based printing, using the preview HTML and template CSS so the visual layout remains consistent with the selected format.

## Reliability, guardrails, and limitations

Preset defaults ensure valid formatting even with partial input. Template boilerplate lines are stripped during parsing to avoid importing publisher instructions into the paper body. When AI enhancement fails, the deterministic formatter is used as a fallback. The main performance cost comes from large documents with tables and equations, which can increase editor render time, and from PDF compilation latency, which depends on LaTeX availability and input complexity.

## Extension ideas

- Add a side-by-side diff between source and formatted output to make layout changes auditable.
- Add a template validation checklist that flags missing sections and style violations before export.
