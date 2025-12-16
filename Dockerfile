# Use a stable, widely supported Python version
FROM python:3.11-slim

# Ensure logs are flushed straight away and no .pyc files
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

# Cloud Run listens on 8080 by default
ENV PORT=8080

# (Opcional) Instalar libs del sistema SOLO si las necesitas.
# Para una API dummy FastAPI normalmente NO hace falta gcc/build-essential/etc.
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip & build tooling
RUN pip install --upgrade pip setuptools wheel

# Create and change to the app directory
WORKDIR /app

# Copy dependency manifests first to leverage Docker layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install -r requirements.txt

# Copy local code
COPY . .

# Run as non-root (más seguro)
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

# (Opcional) Healthcheck - solo sirve si tu app tiene /health
# HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
#   CMD curl -fsS http://127.0.0.1:${PORT}/health || exit 1

# Use gunicorn with uvicorn worker for FastAPI
# - workers: empieza con 1 (Cloud Run escala horizontal)
# - threads: no aplica igual en async, pero lo dejamos simple
# - timeout: 0 para deshabilitar; puedes poner 60/120 si prefieres
CMD exec gunicorn -k uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:${PORT} \
  --workers 1 \
  --timeout 0 \
  main:app
