# CareerOS

**Autonomous AI Career Operating System**

CareerOS is a production-oriented AI career platform that autonomously discovers jobs, matches them against your verified evidence, generates tailored resumes, and assists with applications — all while keeping you in control of irreversible actions.

## Status

**Phase 0 — Foundation** ✅

See [docs/PROJECT_STATE.md](docs/PROJECT_STATE.md) for current build status.

---

## Architecture

- **Backend**: Python / FastAPI / SQLAlchemy / PostgreSQL / pgvector
- **Frontend**: Next.js 14 / TypeScript / Tailwind CSS
- **Queue**: Redis / ARQ
- **Browser Automation**: Playwright
- **Storage**: Local (dev) / S3-compatible (prod)
- **AI/Models**: Ollama (local) / OpenAI-compatible (configurable)

---

## Quick Start

### Prerequisites

- Docker 24+
- Docker Compose 2+

### 1. Clone and configure

```bash
git clone <repo-url>
cd careeros
cp .env.example .env
# Edit .env — set POSTGRES_PASSWORD and other secrets
```

### 2. Start services

```bash
docker compose up
```

Or for development with hot reload:

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up
```

### 3. Access

| Service | URL |
|---------|-----|
| Web UI | http://localhost:3000 |
| API | http://localhost:8000 |
| API Docs | http://localhost:8000/docs |
| Health | http://localhost:8000/health |
| Metrics | http://localhost:8000/metrics |

---

## Development (without Docker)

See [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) for detailed setup instructions.

### Backend

```bash
cd apps/api
python -m venv .venv
# Windows: .venv\Scripts\activate
# Unix: source .venv/bin/activate
pip install -r requirements.txt aiosqlite
pytest tests/
```

### Frontend

```bash
cd apps/web
npm install
npm run dev
```

---

## Core Principles

1. **Truth policy**: Never fabricate candidate information
2. **Evidence graph**: Every claim requires traceable evidence
3. **Human control**: Irreversible actions require human approval
4. **Policy engine**: Configurable autonomy per action type
5. **Security**: Prompt injection defense, browser isolation, audit logs
6. **Observable**: Structured logs, metrics, correlation IDs

---

## License

MIT — See [LICENSE](LICENSE)
