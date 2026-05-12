# ── Stage 1: builder ─────────────────────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /build

# Build-time dependencies needed to compile Python extension modules:
#   build-essential  — gcc/g++ for C extensions (psycopg2, cryptography, etc.)
#   libpq-dev        — PostgreSQL client headers (psycopg2-binary compile)
#   libffi-dev       — libffi headers (cryptography, cffi)
#   libssl-dev       — OpenSSL headers (cryptography)
#   pkg-config       — locate libraries for native builds
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    libffi-dev \
    libssl-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt


# ── Stage 2: runtime ─────────────────────────────────────────────────────────
FROM python:3.11-slim

WORKDIR /app

# Runtime system dependencies:
#   libpq5        — PostgreSQL client library (psycopg2-binary runtime)
#   libffi8       — libffi runtime (cryptography / JWT)
#   poppler-utils — PDF→image conversion used by pdf2image (OCR fallback)
#                   PyMuPDF (fitz) is the primary PDF renderer and needs no
#                   system deps, but pdf2image is kept as a fallback.
#   curl          — health-check probe (Railway, Docker HEALTHCHECK)
#   ca-certificates — HTTPS calls to OpenAI, Supabase, OpenFDA, RxNorm
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    libffi8 \
    poppler-utils \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Copy installed Python packages from builder
COPY --from=builder /install /usr/local

COPY . .

# Create persistent data directories.
# uploads/prescriptions — incoming prescription files (temporary; deleted after OCR)
# uploads/reports       — locally-cached generated PDF reports
# data/guidelines       — clinical guideline documents for RAG
# data/faiss_index      — FAISS vector-store index
RUN mkdir -p \
    uploads/prescriptions \
    uploads/reports \
    generated_reports \
    data/guidelines \
    data/faiss_index

# Non-root user for security (UID 1001 avoids conflicts with common system UIDs)
RUN useradd -m -u 1001 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# Health-check: Railway and docker-compose use this to gate dependent services.
# /health must respond 200 within 10 s; 60 s start-period for migrations.
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Production: uvicorn with 2 workers.
# Override CMD in docker-compose for dev (--reload) or Celery workers.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
