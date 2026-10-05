#!/bin/sh
# CareerOS API entrypoint
# 1. Wait for Postgres to be ready
# 2. Run Alembic migrations
# 3. Start uvicorn

set -e

echo "==> Waiting for database..."
# Retry loop — postgres container may still be initialising
MAX_TRIES=30
i=0
until python -c "
import asyncio, asyncpg, os, sys
async def check():
    url = os.environ.get('DATABASE_URL', '')
    # asyncpg uses postgresql://, not postgresql+asyncpg://
    url = url.replace('postgresql+asyncpg://', 'postgresql://')
    try:
        conn = await asyncpg.connect(url, timeout=5)
        await conn.close()
    except Exception as e:
        sys.exit(1)
asyncio.run(check())
" 2>/dev/null; do
    i=$((i + 1))
    if [ "$i" -ge "$MAX_TRIES" ]; then
        echo "ERROR: Database not reachable after ${MAX_TRIES} attempts. Aborting."
        exit 1
    fi
    echo "  Attempt $i/${MAX_TRIES} — retrying in 2s..."
    sleep 2
done
echo "==> Database is ready."

echo "==> Running Alembic migrations..."
alembic upgrade head
echo "==> Migrations complete."

echo "==> Starting uvicorn..."
exec uvicorn app.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --workers "${UVICORN_WORKERS:-2}" \
    --log-level "$(echo "${LOG_LEVEL:-info}" | tr '[:upper:]' '[:lower:]')"
