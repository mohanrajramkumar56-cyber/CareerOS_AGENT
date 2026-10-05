# Deployment

This document covers how to deploy CareerOS in both development and production configurations.

---

## Prerequisites

| Requirement | Version | Notes |
|---|---|---|
| Docker | 24+ | Required |
| Docker Compose | 2+ | Required |
| Ollama | Latest | Optional — needed for local AI models |
| Git | Any | For cloning |

Ollama is optional. If not running, CareerOS will fall back to an OpenAI-compatible API if `OPENAI_API_KEY` is set. See [ADR-005](ADR/ADR-005-model-routing.md) for model routing details.

---

## Quick Start

### 1. Clone and configure

```bash
git clone <repo-url>
cd careeros
cp .env.example .env
```

Open `.env` and set all values marked `CHANGE_ME`. At minimum:

- `POSTGRES_PASSWORD`
- `JWT_SECRET_KEY`
- `SECRET_KEY`

### 2. Start all services

```bash
docker compose up
```

This starts: PostgreSQL, Redis, the FastAPI backend, the ARQ worker, and the Next.js frontend.

For development with hot reload:

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up
```

### 3. Run database migrations

On first start, run migrations manually if they are not applied automatically:

```bash
docker compose exec api alembic upgrade head
```

### 4. Verify

| Service | URL |
|---|---|
| Web UI | http://localhost:3000 |
| API | http://localhost:8000 |
| API Docs | http://localhost:8000/docs |
| Health check | http://localhost:8000/health |
| Metrics | http://localhost:8000/metrics |

A `200 OK` from `/health` confirms the API, database, and Redis connections are all healthy.

---

## Environment Variables

All configuration is via environment variables. See `.env.example` for the full list with descriptions.

Key variables:

| Variable | Default | Description |
|---|---|---|
| `ENVIRONMENT` | `development` | Set to `production` in prod |
| `POSTGRES_PASSWORD` | `CHANGE_ME` | PostgreSQL password |
| `JWT_SECRET_KEY` | `CHANGE_ME` | JWT signing key |
| `SECRET_KEY` | `CHANGE_ME` | Application secret key |
| `STORAGE_BACKEND` | `local` | `local` or `s3` |
| `BROWSER_TEST_MODE` | `true` | Set `false` for real browser automation |
| `OLLAMA_BASE_URL` | `http://ollama:11434` | Ollama endpoint |
| `OPENAI_API_KEY` | _(empty)_ | Optional OpenAI fallback |
| `SMTP_HOST` | _(empty)_ | Email sending host |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | _(empty)_ | OpenTelemetry collector endpoint |

---

## Database Migrations

CareerOS uses Alembic for schema migrations.

```bash
# Apply all pending migrations
docker compose exec api alembic upgrade head

# Check current migration state
docker compose exec api alembic current

# Create a new migration after model changes
docker compose exec api alembic revision --autogenerate -m "describe your change"
```

Never edit migration files that have already been applied to a shared database.

---

## Production Checklist

Before going live, verify every item on this list:

### Secrets
- [ ] `POSTGRES_PASSWORD` changed from `CHANGE_ME`
- [ ] `JWT_SECRET_KEY` changed from `CHANGE_ME` (use a cryptographically random 32+ byte value)
- [ ] `SECRET_KEY` changed from `CHANGE_ME`
- [ ] No secrets committed to version control (check `.gitignore` includes `.env`)

### Environment
- [ ] `ENVIRONMENT=production` set
- [ ] `DEBUG=false` (or equivalent — do not expose stack traces to clients)

### Storage
- [ ] `STORAGE_BACKEND=s3` configured for multi-instance or durable storage
- [ ] S3 bucket is private (no public-read ACL)
- [ ] `S3_BUCKET_NAME`, `S3_ACCESS_KEY_ID`, `S3_SECRET_ACCESS_KEY`, `S3_REGION` all set
- [ ] Alternatively, `STORAGE_BACKEND=local` is acceptable for single-server deployments with a mounted persistent volume

### Email
- [ ] `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD` configured
- [ ] `SMTP_FROM_ADDRESS` set to a deliverable address

### Browser Automation
- [ ] `BROWSER_TEST_MODE=false` — required for real application submissions
- [ ] Notification system working so human takeover alerts are delivered

### Observability
- [ ] `OTEL_EXPORTER_OTLP_ENDPOINT` set to your collector (Jaeger, Grafana Tempo, etc.)
- [ ] Log aggregation configured (CloudWatch, Loki, Datadog, etc.)
- [ ] `/metrics` endpoint accessible to your Prometheus scraper

### Database
- [ ] `alembic upgrade head` run against the production database
- [ ] Database backups configured and tested
- [ ] pgvector extension enabled (handled by init scripts — verify on first start)

### TLS
- [ ] HTTPS termination configured at the load balancer or reverse proxy
- [ ] `Strict-Transport-Security` header active (set automatically by the app, requires HTTPS)

---

## Health Check

```
GET /health
```

Returns `200 OK` with a JSON body when the service is healthy:

```json
{
  "status": "healthy",
  "database": "connected",
  "redis": "connected",
  "version": "0.1.0"
}
```

Returns `503 Service Unavailable` if any dependency is unreachable. Use this endpoint for load balancer health checks and container orchestrator liveness probes.

---

## Scaling Notes

- **API**: Stateless — scale horizontally behind a load balancer. Ensure `JWT_SECRET_KEY` and `SECRET_KEY` are identical across all instances.
- **Worker**: Multiple ARQ worker instances can run concurrently. Browser automation is capped at 2 concurrent sessions system-wide (configurable via `BROWSER_MAX_CONCURRENT`).
- **Database**: Single PostgreSQL instance is sufficient at current scale. For high availability, use a managed service (RDS, Cloud SQL) with read replicas.
- **Redis**: Single Redis instance is sufficient. For HA, use Redis Sentinel or a managed service (ElastiCache).
- **Storage**: Use `STORAGE_BACKEND=s3` when running multiple API or worker instances so all instances share the same artifact store.
- **Ollama**: Runs as a separate service. If running multiple API instances, point all of them at a single Ollama instance to avoid redundant model loads.
