# Doc Chat Feature

## What does it do?

Doc Chat is a retrieval-augmented conversational interface over uploaded documents. It enables users to ask contextual questions and get source-grounded answers while preserving per-session conversation history.

## How does it work?

- Creates chat sessions and stores message history.
- Accepts one or more user files for ingestion.
- Splits content into chunks, indexes embeddings, and builds keyword index.
- Runs hybrid retrieval and sends context plus history to LLM.
- Returns answer text plus source snippets.

## Technologies used

- Next.js page: web/src/app/doc-chat/page.tsx
- Backend RAG engine: backend/core_agents/rag_agent.py
- SQLAlchemy and SQLite session persistence
- FAISS for vector retrieval and BM25 for lexical retrieval

## Inputs and outputs

- Inputs:
  - session name
  - uploaded files (PDF, DOCX, TXT)
  - natural language questions
- Outputs:
  - assistant answers
  - source references
  - persisted multi-turn history

## API dependencies

- /api/rag/sessions (create/list/delete)
- /api/rag/upload
- /api/rag/query
- /api/rag/messages/{session_id}

## Failure modes and guardrails

- Unsupported file types are blocked during upload.
- Query requires existing session state; empty context is handled with fallback responses.
- Source references are included to improve trust and auditability.

## Performance and scaling notes

- Ingestion cost scales with file count and file size.
- Query latency scales with retrieval depth and model response time.

## Extension ideas

- Add citation-ready answer formatting.
- Add per-message confidence and retrieval diagnostics.
