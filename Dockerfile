# ──────────────────────────────────────────────────────────────
# Grabpic — Dockerfile
#
# Build:  docker build -t grabpic .
# Run:    docker run -p 8000:8000 --env-file .env grabpic
# ──────────────────────────────────────────────────────────────

FROM python:3.12-slim

# System deps — OpenCV + InsightFace need libGL
RUN apt-get update && apt-get install -y --no-install-recommends \
        libgl1 \
        libglib2.0-0 \
        libgomp1 \
        build-essential \
        python3-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install uv (fast Python package manager)
RUN pip install --no-cache-dir uv

# Copy dependency files first (layer cache)
COPY pyproject.toml uv.lock ./

# Install dependencies (no dev deps, no editable)
RUN uv sync --frozen --no-dev

# Pre-download the InsightFace buffalo_l model so cold-starts are instant
# This bakes the ~300 MB weights into the image (avoids runtime download).
RUN uv run python -c "\
from insightface.app import FaceAnalysis; \
fa = FaceAnalysis(name='buffalo_l', providers=['CPUExecutionProvider']); \
fa.prepare(ctx_id=-1, det_size=(640, 640)); \
print('Model pre-loaded OK')"

# Copy application source
COPY . .

# Create storage directory
RUN mkdir -p storage

# Expose the API port
EXPOSE 8000

# Start the server — use Railway's injected $PORT (falls back to 8000 locally)
CMD ["sh", "-c", "uv run uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1"]
