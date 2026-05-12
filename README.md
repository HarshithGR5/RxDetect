# RxDetect

> **AI-powered prescription discrepancy detection.** RxDetect catches errors in handwritten and printed prescriptions before they reach the patient — combining computer vision OCR, deterministic clinical rules, real-time drug validation APIs, RAG-augmented clinical guidelines, and LLM reasoning into a single audit-ready workflow.

---

## Table of Contents

- [Overview](#overview)
- [How It Works](#how-it-works)
- [Discrepancy Classes](#discrepancy-classes)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Getting Started](#getting-started)
  - [Prerequisites](#prerequisites)
  - [Environment Variables](#environment-variables)
  - [Docker Compose (recommended)](#docker-compose-recommended)
  - [Local Development](#local-development)
- [Ingesting Clinical PDFs into the Knowledge Base](#ingesting-clinical-pdfs-into-the-knowledge-base)
- [API Reference](#api-reference)
- [Frontend Pages](#frontend-pages)
- [Contributing](#contributing)
- [License](#license)

---

## Overview

RxDetect automates the first line of clinical safety review — a pharmacist's check that a prescription is complete, consistent, and correctly dosed. A clinician uploads a prescription image or PDF; the system runs it through a six-step AI pipeline and returns a structured discrepancy report with:

- A classification label and confidence score
- Per-rule findings (rule ID, severity, description)
- A 27-parameter clinical audit checklist (YES / NO / N/A)
- Clinical evidence retrieved from the institution's guideline PDFs
- A pharmacist feedback form to correct the AI and close the loop

**Key capabilities**

| Capability | Details |
|---|---|
| OCR extraction | GPT-4o Vision extracts all prescription fields from any image or PDF format |
| 27-parameter checklist | A second GPT-4o call scores 27 clinical parameters (YES / NO / N/A) per prescription |
| Deterministic rule engine | 20+ clinical rules covering dose range, duplicate drugs, allergy flags, missing fields, and illegibility |
| Drug validation | RxNorm + OpenFDA real-time cross-check of drug names, dosage, interactions, and contraindications |
| RAG evidence retrieval | FAISS vector store seeded with your institution's clinical guideline PDFs |
| LLM reasoning | GPT-4o synthesises all signals into a final verdict, confidence score, and clinical narrative |
| PDF audit reports | ReportLab generates downloadable, audit-ready PDFs — generated in-memory, never written to disk |
| Pharmacist feedback loop | Pharmacists can correct AI verdicts; feedback is stored for future model improvement |
| Role-based access | JWT access + refresh tokens; pharmacist / admin / viewer roles |
| Prescription comparison | Side-by-side 27-parameter checklist comparison across any number of analysed prescriptions |

---

## How It Works

Each uploaded prescription is processed asynchronously by a Celery worker through a six-step pipeline:

```
Upload → [Celery queue]
  │
  ├── Step 1: OCR  (GPT-4o Vision)
  │     Extracts: patient demographics, drug names, dosages, frequency,
  │               route, prescriber info, diagnosis, allergy history,
  │               previous medical history, clinic address
  │     Also generates: 27-parameter clinical audit checklist
  │
  ├── Step 2: Rule Engine  (deterministic, 20+ rules)
  │     Checks: missing required fields, dose out of range, duplicate drugs,
  │             contraindication flags, allergy markers, illegibility score
  │
  ├── Step 3: Drug Validation  (RxNorm + OpenFDA)
  │     Validates: drug name spelling, dose units, known drug interactions
  │     Brand → generic mapping: 500+ entries in data/brand_names.csv
  │     Route inference: form prefix (Tab/Syp/Inj/Nasivion/…) → route
  │
  ├── Step 4: RAG Retrieval  (FAISS + clinical guideline PDFs)
  │     Builds a focused per-drug clinical query (filters non-drug tokens)
  │     Retrieves top-k relevant guideline chunks above a relevance threshold
  │
  ├── Step 5: LLM Reasoning  (GPT-4o)
  │     Synthesises rule findings + drug validation + RAG evidence
  │     → discrepancy label + confidence + clinical narrative + therapy suggestions
  │
  └── Step 6: Aggregator
        Consensus logic across rule engine, LLM, and optional ML classifier
        → final verdict written to PostgreSQL
        Status transitions: uploaded → processing → ocr_done → validated → analyzed
```

---

## Discrepancy Classes

| Label | Meaning | Report colour |
|---|---|---|
| **No Discrepancy** | Prescription is clinically complete and consistent | Green |
| **Omission** | A required field or drug information is missing | Amber |
| **Commission** | An incorrect drug, dose, route, or frequency is prescribed | Red |
| **Inconsistency** | Conflicting information within the prescription | Orange |
| **Illegibility** | Cannot reliably extract fields; manual pharmacist review required | Grey |

---

## Tech Stack

### Backend

| Layer | Technology |
|---|---|
| Framework | FastAPI 0.111, Uvicorn, Python 3.11 |
| Database | PostgreSQL 16 + SQLAlchemy 2.0 + Alembic migrations |
| Task queue | Redis 7 + Celery 5.4 + Flower monitoring |
| Auth | python-jose (JWT), passlib/bcrypt |
| AI / LLM | OpenAI GPT-4o (Vision + reasoning) · text-embedding-3-small |
| RAG | LangChain 0.2 · FAISS-CPU vector store |
| Drug APIs | RxNorm (NLM) · OpenFDA |
| PDF generation | ReportLab — pure Python, no system dependencies, streamed in-memory |
| PDF ingestion | PyMuPDF (primary) · pdf2image + Poppler (fallback) |
| NLP | RapidFuzz · ftfy · unidecode |
| ML ensemble | scikit-learn · XGBoost · SHAP explainability |
| Observability | structlog · Sentry |

### Frontend

| Layer | Technology |
|---|---|
| Framework | Next.js 14 (App Router) · TypeScript |
| Styling | Tailwind CSS · custom design tokens (navy `#1B3A6B` · teal `#2EC4B6`) |
| Data fetching | TanStack React Query v5 · Axios with JWT auto-refresh interceptor |
| Animation | Framer Motion |
| Icons | Lucide React |
| File upload | react-dropzone |
| Notifications | react-hot-toast |

### Infrastructure

| Component | Technology |
|---|---|
| Containerisation | Docker · Docker Compose |
| Reverse proxy | Nginx 1.25 |
| DB migrations | Alembic |

---

## Project Structure

```
rxdetect/
├── app/                              # FastAPI backend
│   ├── api/v1/
│   │   ├── auth.py                   # register · login · refresh · logout · /me
│   │   ├── patients.py
│   │   ├── prescriptions.py          # upload · status poll · results · feedback
│   │   └── reports.py                # PDF generation + streaming download
│   ├── models/
│   │   ├── user.py
│   │   ├── prescription.py
│   │   ├── discrepancy_report.py     # stores label · checklist_items · evidence
│   │   ├── patient.py
│   │   └── audit_log.py
│   ├── services/
│   │   ├── ocr/
│   │   │   ├── vision_extractor.py   # GPT-4o Vision + 27-param checklist + route inference
│   │   │   ├── text_cleaner.py
│   │   │   └── confidence.py
│   │   ├── rules/
│   │   │   ├── engine.py             # orchestrates all rule modules
│   │   │   ├── omission_rules.py
│   │   │   ├── commission_rules.py
│   │   │   ├── consistency_rules.py
│   │   │   └── illegibility_rules.py
│   │   ├── validation/
│   │   │   ├── drug_validator.py     # per-drug RxNorm + OpenFDA pipeline
│   │   │   ├── drug_normalizer.py    # brand→generic: CSV → fuzzy → GPT-4o fallback
│   │   │   ├── rxnorm_client.py
│   │   │   └── openfda_client.py
│   │   ├── rag/
│   │   │   ├── retriever.py          # query builder + FAISS search + relevance filter
│   │   │   ├── vector_store.py
│   │   │   ├── embedder.py
│   │   │   └── knowledge_loader.py
│   │   ├── llm/
│   │   │   ├── reasoning_chain.py    # GPT-4o clinical reasoning
│   │   │   ├── classifier.py
│   │   │   └── prompts.py
│   │   ├── ml/
│   │   │   ├── predictor.py          # XGBoost ensemble
│   │   │   └── feature_extractor.py
│   │   ├── aggregator.py             # consensus: rule + LLM + ML → final verdict
│   │   ├── report_generator.py       # ReportLab PDF (sections 1–8 incl. checklist)
│   │   └── worker.py                 # Celery task — full 6-step pipeline
│   ├── config.py                     # pydantic-settings (all env vars)
│   ├── dependencies.py               # DB session · current user
│   └── main.py                       # app factory · CORS · router mount
│
├── frontend/                         # Next.js 14 App Router frontend
│   ├── app/
│   │   ├── page.tsx                  # Landing page (premium SaaS design)
│   │   ├── login/page.tsx
│   │   ├── signup/page.tsx
│   │   ├── dashboard/page.tsx        # Prescription list · stats · multi-select compare bar
│   │   ├── upload/page.tsx           # Drag-and-drop upload · live pipeline progress
│   │   ├── analysis/[id]/page.tsx    # 3-column clinical view · checklist modal · evidence
│   │   ├── compare/page.tsx          # Side-by-side checklist comparison (unlimited Rx)
│   │   └── reports/page.tsx          # All reports · PDF download
│   ├── components/
│   │   ├── Navbar.tsx                # Sticky · glassmorphism · mobile hamburger drawer
│   │   ├── DiscrepancyBadge.tsx
│   │   ├── ClarityIndicator.tsx
│   │   ├── UploadZone.tsx            # Drag-and-drop + mobile camera capture
│   │   ├── FieldExtractPanel.tsx     # Patient & Prescriber sections
│   │   ├── EvidencePanel.tsx         # Collapsible clinical evidence panel
│   │   ├── RuleFindings.tsx          # Collapsible rule findings
│   │   ├── ClinicalChecklistModal.tsx# 27-param Sl.No / YES / NO / N/A table
│   │   ├── StatusPill.tsx
│   │   ├── StatsCard.tsx
│   │   └── Skeleton.tsx
│   ├── lib/
│   │   ├── api.ts                    # Axios client · JWT auto-refresh · all API helpers
│   │   ├── auth.ts                   # setTokens / clearTokens
│   │   ├── types.ts                  # TypeScript interfaces
│   │   └── utils.ts                  # formatDate · formatConfidence · cn helpers
│   ├── middleware.ts                 # Route protection (session cookie check)
│   └── next.config.js
│
├── alembic/                          # Database migration scripts
├── data/
│   ├── brand_names.csv               # 500+ brand→generic drug name mappings
│   ├── faiss_index.faiss             # FAISS vector index (git-ignored)
│   └── faiss_metadata.json           # Index metadata (git-ignored)
├── scripts/
│   └── ingest_pdfs.py                # CLI tool to embed clinical PDFs into FAISS
├── tests/                            # pytest test suite
├── docker-compose.yml
├── Dockerfile
└── requirements.txt
```

---

## Getting Started

### Prerequisites

- **Docker & Docker Compose** v2+ (recommended — all dependencies included)
- **OR** Python 3.11+ and Node.js 20+ for local development
- An **OpenAI API key** with GPT-4o access
- PostgreSQL 16 and Redis 7 (provided automatically via Docker)

---

### Environment Variables

Create a `.env` file in the repo root:

```env
# ── Database ──────────────────────────────────────────────────────────────────
POSTGRES_USER=rxuser
POSTGRES_PASSWORD=changeme
POSTGRES_DB=rxdetect
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
DATABASE_URL=postgresql://rxuser:changeme@localhost:5432/rxdetect

# ── JWT ───────────────────────────────────────────────────────────────────────
JWT_SECRET_KEY=replace_with_a_long_random_string
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=30

# ── OpenAI ────────────────────────────────────────────────────────────────────
OPENAI_API_KEY=sk-...

# ── Redis / Celery ────────────────────────────────────────────────────────────
REDIS_HOST=localhost
REDIS_PORT=6379

# ── Storage ───────────────────────────────────────────────────────────────────
UPLOADS_DIR=uploads
REPORTS_DIR=generated_reports

# ── Frontend (Next.js) ────────────────────────────────────────────────────────
# Create frontend/.env.local with:
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
```

---

### Docker Compose (recommended)

```bash
# 1. Clone the repository
git clone https://github.com/your-username/rxdetect.git
cd rxdetect

# 2. Configure environment
cp .env.example .env
# Edit .env — add OPENAI_API_KEY and a strong JWT_SECRET_KEY

# 3. Start all services (PostgreSQL, Redis, FastAPI, Celery worker, Flower, Nginx)
docker compose up --build

# 4. Start the frontend (in a separate terminal)
cd frontend
cp .env.example .env.local    # set NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
npm install && npm run dev
```

| Service | URL |
|---|---|
| Frontend | http://localhost:5000 |
| Backend API | http://localhost:8000 |
| Swagger UI | http://localhost:8000/docs |
| Celery Flower | http://localhost:5555 |

---

### Local Development

You will need PostgreSQL 16 and Redis 7 running locally.

```bash
# ── Backend ───────────────────────────────────────────────────────────────────
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Apply database migrations
alembic upgrade head

# Start the API server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# In a second terminal — start the Celery worker
celery -A app.services.worker.celery_app worker --loglevel=info -Q analysis

# ── Frontend ──────────────────────────────────────────────────────────────────
cd frontend
npm install
npm run dev       # runs on http://localhost:5000
```

---

## Ingesting Clinical PDFs into the Knowledge Base

The RAG system retrieves relevant clinical guidelines at analysis time from a FAISS vector index. You must run the ingestion script once (or whenever you add new PDFs) to embed the content and build the index.

```bash
# 1. Copy your clinical PDFs into the guidelines directory
cp /path/to/BNF-70.pdf           data/guidelines/
cp /path/to/who_formulary.pdf    data/guidelines/
cp /path/to/clinical_pharm.pdf   data/guidelines/

# 2. Run the ingestion script (one-time; ~30–60 min for 2000 pages)
#    Creates: data/faiss_index.faiss and data/faiss_metadata.json
python scripts/ingest_pdfs.py

# 3. Start the server — the pre-built index loads instantly (< 5 s)
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

**Ingestion script options**

```bash
python scripts/ingest_pdfs.py --help               # show all options
python scripts/ingest_pdfs.py --file new_guide.pdf # add one PDF, keep existing index
python scripts/ingest_pdfs.py --dir /data/guides/  # use a different directory
python scripts/ingest_pdfs.py --reset               # wipe index and rebuild from scratch
python scripts/ingest_pdfs.py --force               # re-embed even already-indexed chunks
```

**Sizing guide**

| Scale | Notes |
|---|---|
| Chunk size | 1000 characters with 150-character overlap (sentence-aware) |
| Index size | FAISS IndexFlatL2 scales to 100k+ vectors on CPU |
| 4 PDFs / ~2000 pages | ~12,000 chunks · ~75 MB index · ~30–60 min to embed (one-time) |
| Retrieval | Millisecond-fast at any scale |

> **Note:** `data/faiss_index.faiss` and `data/faiss_metadata.json` are excluded from git by default (they can be hundreds of MB). Every developer runs the ingestion script once after cloning. Deduplication is MD5-hash based — re-running the script on the same PDF never adds duplicate vectors.

---

## API Reference

Interactive docs: **http://localhost:8000/docs** (Swagger UI) · **http://localhost:8000/redoc**

### Auth

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/v1/auth/register` | Create a new user account |
| `POST` | `/api/v1/auth/login` | Login — returns access + refresh token pair |
| `POST` | `/api/v1/auth/refresh` | Exchange refresh token for a new token pair |
| `DELETE` | `/api/v1/auth/logout` | Revoke the refresh token |
| `GET` | `/api/v1/auth/me` | Get current user profile |

### Prescriptions

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/v1/prescriptions/` | List all prescriptions (paginated, filterable by status) |
| `POST` | `/api/v1/prescriptions/upload` | Upload a prescription image or PDF — triggers the AI pipeline |
| `GET` | `/api/v1/prescriptions/{id}` | Get prescription details |
| `GET` | `/api/v1/prescriptions/{id}/status` | Poll processing status |
| `GET` | `/api/v1/prescriptions/{id}/results` | Get full analysis result |
| `PATCH` | `/api/v1/prescriptions/feedback/{id}` | Submit pharmacist correction / feedback |
| `DELETE` | `/api/v1/prescriptions/{id}` | Soft-delete prescription |

### Reports

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/v1/reports/` | List all generated reports |
| `POST` | `/api/v1/reports/generate/{prescription_id}` | Generate and stream PDF report (in-memory, no disk write) |
| `GET` | `/api/v1/reports/download/{prescription_id}` | Download PDF report |

### Patients

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/v1/patients/` | List patients (searchable) |
| `GET` | `/api/v1/patients/{id}` | Get patient details |

---

## Frontend Pages

| Route | Description |
|---|---|
| `/` | Premium landing page — product overview, pipeline walkthrough, discrepancy type coverage |
| `/login` | Sign in with email + password |
| `/signup` | Create a clinician account with role selection (pharmacist / admin / viewer) |
| `/dashboard` | Prescription list with status filters, search, stats overview, and multi-select compare bar |
| `/upload` | Drag-and-drop upload with camera capture on mobile + real-time pipeline progress |
| `/analysis/[id]` | Full clinical analysis view: extracted fields · rule findings · evidence · 27-param checklist modal · therapy suggestions · pharmacist feedback |
| `/compare?ids=…` | Side-by-side 27-parameter checklist comparison for any number of analysed prescriptions with CSV export |
| `/reports` | All generated reports with PDF download |

---

## Contributing

1. Fork the repository and create your feature branch (`git checkout -b feat/my-feature`)
2. Make your changes and run the test suite (`pytest tests/ -v`)
3. Run the linter (`ruff check app/`) and type checker (`mypy app/`)
4. Open a pull request against `main` with a clear description

---

## License

MIT — see [LICENSE](LICENSE) for details.

> RxDetect is a clinical decision support tool. It does not replace the judgement of a licensed pharmacist or physician. All findings must be verified by a qualified healthcare professional before action is taken.
