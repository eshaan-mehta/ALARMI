# ALARMI backend image — FastAPI on uvicorn, built for Google Cloud Run.
#
# Cloud Run injects $PORT (8080) and runs the container; uvicorn binds it.
# `uv sync --extra gcp` pulls google-cloud-storage (GcsBlobStore); the default
# install stays SQLite + FakeBlobStore, so local dev/tests need no GCP SDK.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

# --- uv (fast, lockfile-driven installs) ---
COPY --from=ghcr.io/astral-sh/uv:0.5 /uv /uvx /bin/

WORKDIR /app

# Install deps first (cached until the lockfile changes). cli.py is copied
# because the project itself is built (hatchling ships cli.py for the entry
# points); --no-dev drops pytest/httpx, --extra gcp adds the deploy deps.
COPY pyproject.toml uv.lock cli.py ./
RUN uv sync --frozen --no-dev --extra gcp

# App code last so edits don't bust the dependency layer.
COPY app ./app

ENV PATH="/app/.venv/bin:$PATH"

# Cloud Run provides $PORT (default 8080). Shell form so the variable expands.
EXPOSE 8080
CMD exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}
