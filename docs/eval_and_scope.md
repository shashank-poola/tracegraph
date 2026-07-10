# TraceGraph — Scope Reality Check

This document exists so interview answers stay honest. The product name and some marketing language can sound like a RAG / search stack. **The implementation is not that.**

## What this system is

**TraceGraph** (repo folder: `graphscope`) builds three artifact layers for a GitHub repo, then uses an LLM to write a **PR blast-radius comment**.

| Layer | How it is produced | Where it lives |
|-------|--------------------|----------------|
| Code | GitHub tarball → Python AST → LLM file/symbol descriptions → optional Neo4j | SQLite `repo_trees` + Neo4j |
| UI | User-supplied routes → browser-use cloud agent → screenshots + labels | SQLite `crawl_results` + `artifacts/` |
| Requirements | Repo `.md`/`.vdk` (or URL/text) → section split → LLM requirements | SQLite `ingest_results` |

PR review loads those artifacts, fetches the PR diff via a **GitHub App**, and posts one upserted comment.

## What this system is not

Verified by searching the codebase (`embed`, `vector`, `redis`, `celery`, `pinecone`, `chroma`, `qdrant`, `faiss`):

| Assumed component | Status in TraceGraph |
|-------------------|----------------------|
| Vector embeddings | **Absent** |
| Chunking for RAG | **Absent** (markdown heading split is for LLM requirement extraction only) |
| Vector DB / semantic search | **Absent** |
| Redis / Celery / durable queue | **Absent** — jobs are `asyncio.create_task` in the API process |
| Dedicated worker fleet | **Absent** |
| Cypher-driven retrieval at PR time | **Absent** — Neo4j is written for exploration; PR reasoning uses SQLite digests in the LLM prompt |
| Automatic URL discovery crawl | **Absent** — routes are user-supplied; sidebar views are expanded from agent output |
| Frontend call to `/graph/connect` | **API exists; dashboard does not call it** (only mentioned in landing FAQ) |

## Interview framing

> “We deliberately did not build a retrieval stack. The hard problem we chose is **linking product intent, live UI, and code structure** for a QA-facing PR comment — not indexing the web or doing semantic search over docs.”

If a founder asks about embeddings or queues, say what is missing and why (local two-process setup, LLM context assembly instead of ANN search). See `docs/system_design.md` for the full architecture and decision log.
