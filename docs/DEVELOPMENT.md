# CareerOS — Development Guide

## Prerequisites

- Python 3.10+
- Node.js 20+
- Docker 24+ (optional, for full stack)
- PostgreSQL 16 (optional, for integration tests)

---

## Backend Setup

```bash
cd apps/api

# Create virtual environment
python -m venv .venv

# Activate (Windows)
.venv\Scripts\activate

# Activate (Unix/macOS)
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Install test deps (already in requirements.txt)
pip install aiosqlite  # SQLite async driver for unit tests
```

### Running the API (development)

```bash
cd apps/api
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Running Tests

Unit tests use SQLite in-memory (no PostgreSQL required):

```bash
cd apps/api
pytest tests/ -v
```

With coverage:

```bash
pytest tests/ --cov=app --cov-report=term-missing
```

### Running Migrations (requires PostgreSQL)

```bash
cd apps/api
# Ensure DATABASE_URL is set in .env
alembic upgrade head
```

---

## Frontend Setup

```bash
cd apps/web
npm install
npm run dev
```

Frontend runs at http://localhost:3000

### Building for Production

```bash
npm run build
npm start
```

---

## Environment Configuration

Copy `.env.example` to `.env`:

```bash
cp .env.example .env
```

Key variables to set:
- `POSTGRES_PASSWORD` — Required, choose a strong password
- `API_SECRET_KEY` — Generate: `openssl rand -hex 32`
- `JWT_SECRET` — Generate: `openssl rand -hex 32`

---

## Docker Development

Full stack with hot reload:

```bash
cp .env.example .env
# Edit .env
docker compose -f docker-compose.yml -f docker-compose.dev.yml up
```

---

## Troubleshooting

### `bcrypt` import errors

The project uses `bcrypt` directly (passlib 1.7.4 is incompatible with bcrypt 4.x). If you see bcrypt errors, ensure bcrypt==4.0.1 is installed.

### SQLite UUID errors in tests

The test suite uses SQLite which handles UUIDs differently than PostgreSQL. The auth endpoint correctly converts string UUIDs to UUID objects before querying. If you see `'str' object has no attribute 'hex'`, check the `get_current_user` function.

### Port conflicts

Default ports:
- PostgreSQL: 5432
- Redis: 6379
- API: 8000
- Web: 3000

Change in `docker-compose.dev.yml` if needed.
