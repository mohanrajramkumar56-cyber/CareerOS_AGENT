# CareerOS Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           CareerOS System                               │
│                                                                         │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────────────────┐│
│  │  Web UI  │   │    API   │   │  Worker  │   │   Browser Worker     ││
│  │(Next.js) │◄──│(FastAPI) │◄──│  (ARQ)   │   │   (Playwright)       ││
│  └──────────┘   └────┬─────┘   └────┬─────┘   └──────────────────────┘│
│                      │              │                                   │
│               ┌──────┴──────────────┴──────┐                          │
│               │      PostgreSQL + pgvector  │                          │
│               └────────────────────────────┘                          │
│                                                                         │
│               ┌────────────────────────────┐                          │
│               │           Redis             │                          │
│               │    (Queue + Cache)          │                          │
│               └────────────────────────────┘                          │
└─────────────────────────────────────────────────────────────────────────┘
```

## Layer Architecture

### API Layer (FastAPI)
```
Request
  → CORS Middleware
  → Correlation ID Middleware
  → Auth Middleware (JWT)
  → Route Handler
  → Service Layer
  → Repository Layer
  → Database (SQLAlchemy Async)
```

### Domain Principle
```
DETERMINISTIC SYSTEMS CONTROL
        ↓
AI RECOMMENDS
        ↓
POLICY VALIDATES
        ↓
TOOLS EXECUTE
        ↓
AUDIT RECORDS
        ↓
HUMAN CONTROLS IRREVERSIBLE ACTIONS
```

### Truth Policy
- Every candidate claim must have evidence
- UNKNOWN > ASSUMED > GENERATED
- LLMs can never fabricate candidate information
- Resume claims must map to evidence nodes

## Database Schema (Phase 0)

```
users
  ├── id (UUID PK)
  ├── email (unique)
  ├── hashed_password
  ├── is_active
  ├── is_verified
  ├── created_at / updated_at / deleted_at
  └── sessions → user_sessions

user_sessions
  ├── id (UUID PK)
  ├── user_id (FK → users)
  ├── refresh_token_hash
  ├── expires_at
  └── ip_address / user_agent
```

## API Versioning

All API routes are versioned: `/api/v1/`

## Security Model

- JWT access tokens (60 min default)
- JWT refresh tokens (30 days default)
- bcrypt password hashing (rounds=12)
- Soft delete on users
- User-scoped resource access (multi-tenant ready)
- CORS configured per environment

## Observability

- Structured JSON logs (structlog)
- Correlation IDs per request (X-Correlation-ID header)
- Prometheus metrics at `/metrics`
- Health check at `/health`
- Readiness check at `/ready`
