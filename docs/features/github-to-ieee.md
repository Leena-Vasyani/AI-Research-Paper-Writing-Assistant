# GitHub-to-IEEE Feature

## What does it do?

GitHub-to-IEEE converts a public GitHub repository into a structured, IEEE-style research paper draft and exports it as both structured text (markdown-like sections) and a PDF artifact. The feature is designed for project-based research writing where the primary evidence is the repository itself: code structure, README documentation, configuration files, and module-level organization. Instead of manually translating a codebase into a narrative, the feature extracts technical signals from the repository and composes a draft that follows academic conventions such as abstract, introduction, methodology, system architecture, evaluation, and conclusion. The output is intended to be a starting point for authors to edit and expand rather than a final submission-ready paper.

## How does it work?

The pipeline follows a data-first approach that separates repository understanding from text generation:

1. Repository identification: the system parses the GitHub URL and resolves the owner and repository name. Invalid formats are rejected early to avoid unnecessary API calls.
2. Metadata collection: the GitHub REST API is used to retrieve high-level metadata (repository description, language signals, README content, and file tree). This stage provides a compact summary of the project context before deeper analysis.
3. File selection and filtering: the file tree is traversed and filtered by extension and size to keep the analysis focused on meaningful source files and documentation. Large or irrelevant files are excluded to control noise and reduce model context cost.
4. Semantic context building: the filtered files are chunked and embedded, then indexed using the FAISS/LangChain retrieval stack. This allows the generator to query the most relevant segments when drafting specific sections (for example, system architecture or implementation details).
5. Structured analysis: the LLM generates a structured JSON-style interpretation of the repository, capturing purpose, core modules, data flow, and external dependencies. This structured representation serves as an intermediate artifact that improves consistency across sections.
6. Section drafting: the drafting stage composes a paper-like narrative in IEEE style. Sections are created with academic tone, and each section is grounded in retrieved code and documentation evidence rather than hallucinated content.
7. PDF rendering: the final draft is converted into a ReportLab-based PDF. The PDF path is separate from the text-generation path, enabling stable output formatting even when the source text changes.

This architecture makes the feature robust to repository variability while preserving traceability from output text back to repository artifacts.

## Technologies used

- Next.js page: web/src/app/github-to-ieee/page.tsx
- Backend generator: backend/core_agents/github_paper_agent.py
- External systems:
  - GitHub REST API
  - LLM providers via shared llm_provider
- ReportLab for PDF generation
- FAISS/LangChain ecosystem for context retrieval

## Inputs and outputs

Inputs are minimal to keep the interface lightweight:

- GitHub repository URL (required)
- Optional paper title or theme hints (optional)

The outputs include:

- A generated, sectioned paper draft in IEEE research style
- A metadata summary for quick review (repository scope, language signals, key modules)
- PDF bytes suitable for download and local archiving

## API dependencies

- /api/github-to-ieee
- /api/github-to-ieee/pdf

## Failure modes and guardrails

The feature includes multiple guardrails to maintain reliability. Invalid or inaccessible repositories are detected early with explicit error messages. GitHub rate limits are surfaced with clear hints for retry or token-based access. The file filtering step limits content by extension and size, preventing oversized binaries or vendor files from polluting the context. When a provider fails to respond or returns incomplete analysis, the system can fall back to alternate providers, improving success rates during transient outages.

## Performance and scaling notes

Performance is dominated by API calls and LLM latency. Large repositories amplify fetch time, embedding time, and retrieval complexity, while strict rate limits can throttle throughput. The semantic indexing stage improves drafting quality but introduces additional processing overhead. In practice, this makes the feature well-suited for small-to-medium repositories and still usable for larger projects with careful filtering.

## Extension ideas

- Add branch/tag selection to target releases or stable snapshots.
- Add architecture diagram extraction from code structure for richer system sections.
