FROM python:3.10-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Build context is repo root — path is relative to repo root
COPY apps/worker/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy worker source
COPY apps/worker/ .

# Copy API source so "from app.*" imports work at build time
# (also mounted as volume at runtime for live updates)
COPY apps/api/ /api/

# Non-root user
RUN useradd -m -u 1000 careeros && chown -R careeros:careeros /app /api
USER careeros

CMD ["python", "-m", "arq", "app.main.WorkerSettings"]
