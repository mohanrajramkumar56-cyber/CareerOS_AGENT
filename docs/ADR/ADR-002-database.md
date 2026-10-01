# ADR-002: Database

**Date:** 2026-10-01
**Status:** Accepted

## Context

CareerOS needs:
- Relational data (users, jobs, applications, evidence, audit)
- Vector similarity search (job matching, semantic search)
- ACID transactions for state machine transitions
- Multi-tenant isolation

## Decision

Use **PostgreSQL 16** with **pgvector** extension.

- SQLAlchemy 2.0 async as ORM
- Alembic for schema migrations
- pgvector for embedding-based similarity search

## Rationale

- PostgreSQL is production-grade, battle-tested, open-source
- pgvector integrates natively, avoiding a separate vector database
- Single database reduces operational complexity
- Strong support for JSONB, arrays, full-text search

## Consequences

- pgvector is required in the Docker image (pgvector/pgvector:pg16)
- Vector columns added to models as needed (Phase 3+)
- Unit tests use SQLite in-memory (pgvector not available in SQLite)
- Integration tests require real PostgreSQL

## Rejected Alternatives

- **MySQL**: No pgvector equivalent, weaker JSON support
- **MongoDB**: No strong ACID, schema flexibility not needed here
- **Separate Pinecone/Weaviate**: Additional service, vendor lock-in
