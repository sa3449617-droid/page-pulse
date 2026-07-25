FROM python:3.11-slim

WORKDIR /app

# Install system dependencies (only what's needed for httpx/ssl)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app source
COPY . .

# Render provides PORT env var; default 8000 for local dev
EXPOSE 8000

# Shell form (not exec form) so $PORT gets expanded
CMD uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}
