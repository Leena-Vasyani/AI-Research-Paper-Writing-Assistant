# RAG Agent

## Module

- backend/core_agents/rag_agent.py

## What does it do?

RAG Agent powers conversational document QA with session persistence, hybrid retrieval, and source-attributed answers.

## How does it work?

- Session management:
  - creates and lists chat sessions
  - persists chat messages in SQLite
- Document ingestion:
  - parses uploaded files
  - chunks text
  - builds FAISS vector store
  - builds BM25 keyword index
- Query flow:
  - runs hybrid retrieval (vector + lexical)
  - fuses candidates with reciprocal rank fusion
  - combines context with chat history
  - calls LLM and stores reply with sources

## Technologies used

- SQLAlchemy + SQLite for sessions/messages
- LangChain document primitives
- FAISS vector store
- BM25 lexical retrieval
- Shared llm_provider for generation

## Inputs and outputs

- Inputs:
  - session_id
  - uploaded files
  - user question
- Outputs:
  - answer text
  - source list
  - persistent message history

## API dependency

- /api/rag/sessions\*
- /api/rag/upload
- /api/rag/query
- /api/rag/messages/{session_id}

## Failure modes and guardrails

- Removes in-memory indexes when sessions are deleted.
- Handles missing session and empty context states safely.
- Keeps persistent data in repository data directory for durability.

## Performance notes

- Ingestion is batch-heavy; query path is lower latency after indexes are built.
- Retrieval depth and chunk size tuning strongly affect response quality.

## Extension ideas

- Add incremental indexing for new files in existing sessions.
- Add reranker stage before final context assembly.
