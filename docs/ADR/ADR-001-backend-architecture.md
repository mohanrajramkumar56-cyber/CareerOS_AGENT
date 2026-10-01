# ADR-001: Backend Architecture

**Date:** 2026-10-01
**Status:** Accepted

## Context

CareerOS requires a backend that is:
- Async-native (browser automation, multiple concurrent job sources)
- Fast to iterate on
- Well-typed
- Easy to test
- Production-grade

## Decision

Use **Python + FastAPI** with:
- SQLAlchemy 2.0 async ORM
- Alembic for migrations
- asyncpg for PostgreSQL driver
- structlog for structured logging
- pydantic-settings for configuration
- ARQ for background tasks

## Rationale

- FastAPI is async-native, provides auto-generated OpenAPI docs
- Python ecosystem has strong AI/ML library support (for model integration)
- SQLAlchemy 2.0 async supports our use of PostgreSQL + pgvector
- ARQ is a Redis-backed async task queue that fits the async model

## Consequences

- All I/O must be async
- Sync operations (bcrypt) are acceptable in non-hot paths
- Workers share the same SQLAlchemy models

## Rejected Alternatives

- **Django**: Sync by default, heavier for this use case
- **Node.js/Express**: Weaker AI/ML ecosystem
- **Go**: Weaker AI library ecosystem
