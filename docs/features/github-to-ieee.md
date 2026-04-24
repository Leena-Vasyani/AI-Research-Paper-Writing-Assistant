# GitHub-to-IEEE Feature

## What does it do?

GitHub-to-IEEE converts a public GitHub repository into an IEEE-style research paper draft and exports it as both markdown-like structured content and PDF output.

## How does it work?

- Parses repository URL and extracts owner/repo.
- Calls GitHub REST APIs for metadata, README, tree, and file contents.
- Performs repository analysis via LLM-generated structured JSON.
- Builds semantic context from code and docs.
- Generates paper sections in IEEE research style.
- Produces downloadable PDF via ReportLab-based pipeline.

## Technologies used

- Next.js page: web/src/app/github-to-ieee/page.tsx
- Backend generator: backend/core_agents/github_paper_agent.py
- External systems:
  - GitHub REST API
  - LLM providers via shared llm_provider
- ReportLab for PDF generation
- FAISS/LangChain ecosystem for context retrieval

## Inputs and outputs

- Inputs:
  - GitHub repository URL
  - optional paper title/theme hints
- Outputs:
  - generated sectioned paper
  - metadata summary
  - PDF bytes for download

## API dependencies

- /api/github-to-ieee
- /api/github-to-ieee/pdf

## Failure modes and guardrails

- Handles invalid GitHub URLs and missing repositories.
- Handles GitHub rate limit with clear error hints.
- Restricts file inclusion by extension and size to control noise.

## Performance and scaling notes

- Large repositories increase fetch and analysis latency.
- API limits and provider latency are dominant runtime factors.

## Extension ideas

- Add branch/tag selection support.
- Add architecture diagram extraction from code structure.
