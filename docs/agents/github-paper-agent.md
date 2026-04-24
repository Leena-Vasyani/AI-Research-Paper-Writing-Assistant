# GitHub Paper Agent

## Module

- backend/core_agents/github_paper_agent.py

## What does it do?

GitHub Paper Agent analyzes a repository and generates a structured IEEE-style research paper, including optional PDF export.

## How does it work?

- URL parsing:
  - validates github.com repository URLs
  - extracts owner and repo names
- Repository acquisition:
  - fetches metadata, README, language stats, file tree, selected file contents
  - applies extension and size filtering
- LLM analysis:
  - requests structured JSON fields such as purpose, architecture, innovation, scalability
- Context pipeline:
  - builds vectorstore from repository text
  - retrieves relevant snippets for section drafting
- Paper generation:
  - composes abstract/introduction/method/results/discussion-style sections
- PDF generation:
  - uses ReportLab to render section text into downloadable PDF

## Technologies used

- GitHub REST API
- LangChain + FAISS ecosystem
- shared llm_provider for model fallback
- ReportLab for PDF creation

## Inputs and outputs

- Input:
  - GitHub repository URL
- Output:
  - structured paper content
  - analysis metadata
  - PDF bytes/file output path depending on endpoint

## API dependency

- /api/github-to-ieee
- /api/github-to-ieee/pdf

## Failure modes and guardrails

- Handles rate limiting, invalid repos, and inaccessible resources.
- Restricts oversized files to control cost and noise.
- Falls back with default analysis structure if JSON parse fails.

## Performance notes

- End-to-end latency can be high for repositories with many relevant files.

## Extension ideas

- Add repository snapshot caching keyed by commit SHA.
- Add reproducibility appendix generation from dependency files.
