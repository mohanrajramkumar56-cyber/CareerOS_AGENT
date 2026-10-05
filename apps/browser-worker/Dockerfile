FROM python:3.10-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    libnss3 \
    libatk-bridge2.0-0 \
    libdrm2 \
    libxkbcommon0 \
    libgbm1 \
    libgtk-3-0 \
    libasound2 \
    libxshmfence1 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    fonts-liberation \
    xvfb \
    && rm -rf /var/lib/apt/lists/*

# Build context is repo root — path is relative to repo root
COPY apps/browser-worker/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright Chromium browser
RUN python -m playwright install chromium --with-deps || true

# Copy browser-worker source
COPY apps/browser-worker/ .

# Copy API source so "from app.*" imports work
COPY apps/api/ /api/

# Non-root user
RUN useradd -m -u 1000 careeros && chown -R careeros:careeros /app /api
USER careeros

CMD ["python", "-m", "arq", "app.main.BrowserWorkerSettings"]
