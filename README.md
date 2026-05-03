# RxDetect — AI-Powered Prescription Discrepancy Detection System

> A hospital-grade clinical platform that uses OCR, rule engines, RAG (Retrieval-Augmented Generation), drug validation APIs, and LLM clinical reasoning to automatically detect errors in handwritten and printed prescriptions.

---

## Table of Contents

- [Overview](#overview)
- [Discrepancy Classes](#discrepancy-classes)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Getting Started](#getting-started)
  - [Prerequisites](#prerequisites)
  - [Environment Variables](#environment-variables)
  - [Run with Docker Compose](#run-with-docker-compose)
  - [Run Locally (without Docker)](#run-locally-without-docker)
- [Knowledge Base — Ingesting Clinical PDFs](#knowledge-base--ingesting-clinical-pdfs)
- [API Reference](#api-reference)
- [Frontend Pages](#frontend-pages)
- [AI Pipeline](#ai-pipeline)
- [Contributing](#contributing)
- [License](#license)

---

## Overview

RxDetect automates the pharmacist's first line of defence — catching prescription errors before they reach the patient. A clinician uploads a prescription image; the system runs it through a multi-stage AI pipeline and returns a structured discrepancy report with a confidence score, supporting evidence from WHO drug guidelines, and a pharmacist feedback loop for continuous model improvement.

**Key capabilities**

| Capability | Details |
|---|---|
| OCR extraction | GPT-4o Vision extracts all prescription fields from any image format |
| Rule engine | 20+ deterministic clinical rules (dose range, duplicate drug, allergy flag, …) |
| Drug validation | RxNorm + OpenFDA real-time cross-check of drug names, dosage, and interactions |
| RAG evidence | FAISS vector store seeded with WHO essential medicines guidelines (89 chunks) |
| LLM reasoning | GPT-4o synthesises all signals into a final clinical verdict |
| PDF reports | WeasyPrint generates a downloadable audit-ready PDF per prescription |
| Role-based auth | JWT access + refresh tokens; pharmacist / doctor / admin roles |

---

## Discrepancy Classes

| Label | Meaning | UI colour |
|---|---|---|
| **No Discrepancy** | Prescription is clinically sound | Green |
| **Omission** | Required field or drug is missing | Amber |
| **Commission** | Incorrect drug, dose, or route prescribed | Red |
| **Inconsistency** | Conflicting information within the prescription | Orange |
| **Illegibility** | Cannot reliably extract fields; manual review needed | Gray |

---

## Architecture

```
Browser (Next.js 14)
        │  REST/JSON + Bearer token
        ▼
FastAPI backend (port 8000)
   ├── Auth  →  JWT (access 15 min / refresh 30 days)
   ├── Prescriptions  →  upload → Celery queue → AI pipeline
   ├── Reports  →  PDF generation + authenticated download
   └── Patients
        │
        ├── PostgreSQL 16  (users, prescriptions, reports, audit log)
        ├── Redis 7         (Celery broker + result backend)
        └── FAISS index     (WHO guideline embeddings, 89 vectors)

AI Pipeline (Celery worker)
   Step 1 │ GPT-4o Vision  →  OCR field extraction
   Step 2 │ Rule Engine    →  deterministic clinical checks
   Step 3 │ RxNorm/OpenFDA →  drug name & dose validation
   Step 4 │ FAISS RAG      →  retrieve relevant WHO guidelines
   Step 5 │ GPT-4o         →  synthesise verdict + confidence score
   Step 6 │ Aggregator     →  consensus across all signals
```

---

## Tech Stack

### Backend
| Layer | Technology |
|---|---|
| Framework | FastAPI 0.111, Uvicorn, Python 3.11 |
| Database | PostgreSQL 16 + SQLAlchemy 2.0 + Alembic |
| Cache / Queue | Redis 7, Celery 5.4, Flower |
| Auth | python-jose (JWT), passlib/bcrypt |
| AI / LLM | OpenAI GPT-4o (vision + reasoning), text-embedding-3-small |
| RAG | LangChain 0.2, FAISS-CPU |
| Drug APIs | RxNorm (NLM), OpenFDA |
| PDF | WeasyPrint + Jinja2 |
| NLP | RapidFuzz, ftfy, unidecode |
| ML | scikit-learn, XGBoost, SHAP |
| Observability | structlog, Sentry |

### Frontend
| Layer | Technology |
|---|---|
| Framework | Next.js 14 (App Router), TypeScript |
| Styling | Tailwind CSS, custom design tokens |
| Data fetching | TanStack React Query v5, Axios |
| Animation | Framer Motion |
| Icons | Lucide React |
| File upload | react-dropzone |
| Notifications | react-hot-toast |

### Infrastructure
| Component | Technology |
|---|---|
| Container | Docker + Docker Compose |
| Reverse proxy | Nginx 1.25 |
| Migrations | Alembic |

---

## Project Structure

```
rxdetect/
├── app/                        # FastAPI backend
│   ├── api/
│   │   └── v1/
│   │       ├── auth.py         # register, login, refresh, logout
│   │       ├── patients.py
│   │       ├── prescriptions.py
│   │       └── reports.py
│   ├── models/
│   │   ├── user.py
│   │   ├── prescription.py
│   │   ├── discrepancy_report.py
│   │   ├── patient.py
│   │   └── audit_log.py
│   ├── services/
│   │   ├── ocr/                # GPT-4o Vision extraction
│   │   ├── rules/              # deterministic clinical rule engine
│   │   ├── validation/         # RxNorm + OpenFDA drug validation
│   │   ├── rag/                # FAISS vector store + WHO guidelines
│   │   ├── llm/                # GPT-4o clinical reasoning
│   │   ├── ml/                 # XGBoost ensemble + SHAP explainability
│   │   ├── aggregator.py       # multi-signal consensus
│   │   ├── report_generator.py # WeasyPrint PDF generation
│   │   └── worker.py           # Celery task definitions
│   ├── config.py               # pydantic-settings (all env vars)
│   ├── dependencies.py         # DB session, current user
│   └── main.py                 # app factory, CORS, router mount
│
├── frontend/                   # Next.js 14 frontend
│   ├── app/
│   │   ├── page.tsx            # Landing page
│   │   ├── login/page.tsx
│   │   ├── signup/page.tsx
│   │   ├── dashboard/page.tsx  # Prescription list + stats
│   │   ├── upload/page.tsx     # Drag-and-drop upload
│   │   ├── analysis/[id]/      # 3-column clinical analysis view
│   │   └── reports/page.tsx    # All reports + PDF download
│   ├── components/
│   │   ├── Navbar.tsx
│   │   ├── DiscrepancyBadge.tsx
│   │   ├── ClarityIndicator.tsx
│   │   ├── UploadZone.tsx
│   │   ├── FieldExtractPanel.tsx
│   │   ├── EvidencePanel.tsx
│   │   ├── RuleFindings.tsx
│   │   ├── StatusPill.tsx
│   │   ├── StatsCard.tsx
│   │   └── Skeleton.tsx
│   ├── lib/
│   │   ├── api.ts              # Axios client, token management, all API helpers
│   │   ├── auth.ts             # setTokens / clearTokens re-exports
│   │   ├── types.ts            # shared TypeScript interfaces
│   │   └── utils.ts            # formatDate, formatConfidence, cn helpers
│   ├── middleware.ts           # route protection (rx_session cookie check)
│   └── next.config.js
│
├── alembic/                    # DB migration scripts
├── data/                       # FAISS index + WHO guideline docs
├── tests/                      # pytest test suite
├── docker-compose.yml
├── Dockerfile
└── requirements.txt
```

---

## Getting Started

### Prerequisites

- **Docker & Docker Compose** v2+ (recommended)
- **OR** Python 3.11+ and Node.js 20+ for local development
- An **OpenAI API key** (GPT-4o access required)
- PostgreSQL 16 and Redis 7 (provided automatically via Docker)

---

### Environment Variables

Copy the example below to a `.env` file in the repo root before starting.

```env
# ── Database ─────────────────────────────────────────────────────────────────
POSTGRES_USER=rxuser
POSTGRES_PASSWORD=changeme
POSTGRES_DB=rxdetect
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
DATABASE_URL=postgresql://rxuser:changeme@localhost:5432/rxdetect

# ── JWT ──────────────────────────────────────────────────────────────────────
JWT_SECRET_KEY=replace_with_a_long_random_string
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=30

# ── OpenAI ───────────────────────────────────────────────────────────────────
OPENAI_API_KEY=sk-...

# ── Redis / Celery ───────────────────────────────────────────────────────────
REDIS_HOST=localhost
REDIS_PORT=6379

# ── Storage ──────────────────────────────────────────────────────────────────
UPLOADS_DIR=uploads
REPORTS_DIR=generated_reports

# ── Frontend (Next.js) ───────────────────────────────────────────────────────
# Create frontend/.env.local with:
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
```

---

### Run with Docker Compose

```bash
# 1. Clone the repo
git clone https://github.com/your-username/rxdetect.git
cd rxdetect

# 2. Create environment file
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY and a strong JWT_SECRET_KEY

# 3. Start all services (PostgreSQL, Redis, FastAPI, Celery, Flower, Nginx)
docker compose up --build

# 4. In a separate terminal, start the frontend
cd frontend
cp .env.example .env.local    # set NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
npm install
npm run dev
```

Services will be available at:

| Service | URL |
|---|---|
| Frontend | http://localhost:5000 |
| Backend API | http://localhost:8000 |
| API Docs (Swagger) | http://localhost:8000/docs |
| Celery Flower | http://localhost:5555 |

---

### Run Locally (without Docker)

You will need PostgreSQL 16 and Redis 7 running on your machine.

```bash
# ── Backend ──────────────────────────────────────────────────────────────────
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Apply DB migrations
alembic upgrade head

# Start API server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# In a second terminal — start Celery worker
celery -A app.services.worker.celery_app worker --loglevel=info -Q analysis

# ── Frontend ─────────────────────────────────────────────────────────────────
cd frontend
npm install
npm run dev                        # runs on http://localhost:5000
```

---

## Knowledge Base — Ingesting Clinical PDFs

The RAG system uses a FAISS vector index seeded with your clinical guideline PDFs.
**Do not** drop PDFs into `data/guidelines/` and restart the server — the ingestion
script must be run first so embeddings are generated and saved offline.

### How large a corpus can it handle?

| Scale | Details |
|---|---|
| Chunk size | 1000 characters with 150-char overlap (sentence-aware) |
| Batch limit | OpenAI API limit (2048 items) is handled automatically — 12,000 chunks = 6 auto-batches |
| Index size | FAISS IndexFlatL2 scales to 100k+ vectors on CPU; 12,000 chunks ≈ 75 MB RAM |
| 4 PDFs / 2000 pages | ~12,000 chunks, ~75 MB index, ~30–60 min to embed (one-time, billed per token) |
| Retrieval | Millisecond-fast at any scale using approximate nearest-neighbour search |

### Step-by-step: adding your 4 clinical PDFs

```bash
# 1. Copy your PDFs into the guidelines directory
cp /path/to/your/clinical_pharmacy_vol1.pdf  data/guidelines/
cp /path/to/your/clinical_pharmacy_vol2.pdf  data/guidelines/
cp /path/to/your/medicine_reference.pdf      data/guidelines/
cp /path/to/your/who_formulary.pdf           data/guidelines/

# 2. Run the ingestion script (one-time; takes 30–60 min for 2000 pages)
#    This creates/updates data/faiss_index.faiss and data/faiss_metadata.json
python scripts/ingest_pdfs.py

# 3. Start the server — it loads the pre-built index instantly (< 5 seconds)
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Ingestion script options

```bash
# Show what's already in the index
python scripts/ingest_pdfs.py --help

# Add a single new PDF without touching the existing index
python scripts/ingest_pdfs.py --file data/guidelines/new_drug_monographs.pdf

# Use a different directory
python scripts/ingest_pdfs.py --dir /data/my_guidelines/

# Wipe the index and rebuild everything from scratch
python scripts/ingest_pdfs.py --reset

# Force re-embed even chunks that are already indexed
python scripts/ingest_pdfs.py --force
```

### What the index tracks per chunk

| Field | Example |
|---|---|
| `text` | The 1000-char chunk of clinical text |
| `source` | `clinical_pharmacy_vol1.pdf \| p.142` |
| `page` | `142` |
| `file` | `clinical_pharmacy_vol1.pdf` |
| `score` | `0.84` (relevance score at query time) |

### Important notes

- The FAISS index files (`data/faiss_index.faiss`, `data/faiss_metadata.json`) are
  excluded from git by default (they can be hundreds of MB). Each developer runs
  the ingest script locally once after cloning.
- Deduplication is MD5-hash based — re-running the script on the same PDF never
  adds duplicate vectors.
- The server never rebuilds the index at startup if the index file already exists;
  startup time is always fast regardless of index size.

---

## API Reference

Full interactive docs are available at **http://localhost:8000/docs** (Swagger UI) and **http://localhost:8000/redoc**.

### Auth

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/v1/auth/register` | Create a new user account |
| `POST` | `/api/v1/auth/login` | Login, returns access + refresh tokens |
| `POST` | `/api/v1/auth/refresh` | Exchange refresh token for a new token pair |
| `DELETE` | `/api/v1/auth/logout` | Revoke refresh token |
| `GET` | `/api/v1/auth/me` | Get current user profile |

### Prescriptions

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/v1/prescriptions/` | List all prescriptions (paginated, filterable by status) |
| `POST` | `/api/v1/prescriptions/upload` | Upload a prescription image — triggers AI pipeline |
| `GET` | `/api/v1/prescriptions/{id}` | Get prescription details |
| `GET` | `/api/v1/prescriptions/{id}/status` | Poll processing status |
| `GET` | `/api/v1/prescriptions/{id}/results` | Get full analysis result |
| `PATCH` | `/api/v1/prescriptions/feedback/{id}` | Submit pharmacist correction/feedback |
| `DELETE` | `/api/v1/prescriptions/{id}` | Delete prescription |

### Reports

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/v1/reports/` | List all generated reports |
| `POST` | `/api/v1/reports/generate/{prescription_id}` | Generate PDF report |
| `GET` | `/api/v1/reports/download/{prescription_id}` | Download PDF (authenticated) |

### Patients

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/v1/patients/` | List patients (searchable) |
| `GET` | `/api/v1/patients/{id}` | Get patient details |

---

## Frontend Pages

| Route | Description |
|---|---|
| `/` | Landing page — product overview |
| `/login` | Sign in with email + password |
| `/signup` | Create a new clinician account |
| `/dashboard` | Prescription list with status filters and summary stats |
| `/upload` | Drag-and-drop prescription image upload |
| `/analysis/[id]` | 3-column clinical view: extracted fields · rule findings · guideline evidence |
| `/reports` | All generated reports with PDF download |

---

## AI Pipeline

Each uploaded prescription is processed asynchronously through a 6-step pipeline:

```
Upload → [Celery queue]
  │
  ├── Step 1: OCR (GPT-4o Vision)
  │     Extracts: patient name, drug names, dosages, frequency,
  │               route, prescriber, date, diagnosis
  │
  ├── Step 2: Rule Engine (20+ deterministic rules)
  │     Checks: dose range, duplicate drug, missing fields,
  │             contraindication flags, allergy markers
  │
  ├── Step 3: Drug Validation (RxNorm + OpenFDA)
  │     Validates: drug name spelling, dose units, known interactions
  │
  ├── Step 4: RAG Retrieval (FAISS + WHO guidelines)
  │     Retrieves: top-k relevant guideline chunks for drugs found
  │
  ├── Step 5: LLM Reasoning (GPT-4o)
  │     Synthesises all signals → discrepancy label + confidence score
  │     + clinical reasoning narrative
  │
  └── Step 6: Aggregator
        Consensus across rule engine + LLM → final verdict stored to DB
        Status transitions: uploaded → ocr_done → validated → analyzed
```

---

## Contributing

1. Fork the repository and create a feature branch: `git checkout -b feat/your-feature`
2. Install pre-commit hooks: `pre-commit install`
3. Write tests for new backend logic in `tests/`
4. Run the test suite: `pytest --cov=app tests/`
5. Lint: `ruff check . && mypy app/`
6. Open a pull request with a clear description of the change

---

## License

This project is licensed under the **MIT License** — see [LICENSE](LICENSE) for details.

---

> Built for clinical environments. Always verify AI-generated discrepancy findings with a qualified pharmacist or prescriber before acting on them.
