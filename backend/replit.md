# RxDetect — AI-Assisted Prescription Safety System

## Architecture Overview

Full-stack clinical decision support system for detecting prescription discrepancies.

### Backend (FastAPI / Python 3.11)
- **Entry point:** `app/main.py`
- **Port:** 8000
- **Framework:** FastAPI + SQLAlchemy + Alembic
- **Auth:** JWT (OAuth2 Bearer), roles: pharmacist / admin / viewer
- **API prefix:** `/api/v1`
- **Routes:** `/auth`, `/patients`, `/prescriptions`, `/reports`

### Frontend (Next.js 14 / TypeScript)
- **Directory:** `frontend/`
- **Port:** 5000 (webview)
- **Framework:** Next.js App Router + TailwindCSS + TanStack React Query + Framer Motion
- **Design:** Clinical EHR aesthetic — Deep Blue (#0B3C5D) primary, Teal (#2EC4B6) secondary
- **API proxy:** `/api/*` rewrites to `http://localhost:8000/api/*` via `next.config.js`

### Pages
| Route | Description |
|-------|-------------|
| `/` | Landing page — product overview, features, pipeline |
| `/login` | JWT login (OAuth2 form) |
| `/signup` | Role-based registration (pharmacist / admin / viewer) |
| `/dashboard` | Prescription list with status/discrepancy filters + stats |
| `/upload` | Drag-and-drop upload + live pipeline progress polling |
| `/analysis/[id]` | Full analysis: extracted fields, discrepancy result, rule findings, guideline evidence, pharmacist feedback |
| `/reports` | All reports with discrepancy summary, PDF download |

### Key Components
- `DiscrepancyBadge` — colored badge for 5 discrepancy labels
- `ClarityIndicator` — OCR readability bar (renamed from confidence)
- `UploadZone` — dropzone with preview and loading overlay
- `FieldExtractPanel` — extracted fields with flagged/missing highlighting
- `EvidencePanel` — RAG guideline evidence with relevance scores
- `RuleFindings` — rule engine violations with severity levels
- `StatusPill` — animated prescription status badge
- `StatsCard` — dashboard metric card with motion

### Analysis Pipeline (Backend)
1. Upload → OCR via GPT-4o Vision
2. Drug normalization (greedy longest-match)
3. RxNorm lookup + OpenFDA drug validation
4. Rule engine checks (omission, commission, illegibility, inconsistency)
5. RAG retrieval (FAISS + WHO guidelines)
6. LLM clinical reasoning (GPT-4 with FDA context)
7. Aggregation → discrepancy label + confidence
8. PDF report generation

### Workflows
- `Backend API` — `uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload`
- `Frontend` — `cd frontend && npm run dev` (port 5000)

### Important Notes
- CORS allows `*.replit.dev` via regex
- Frontend auth uses js-cookie (access_token: 15min, refresh_token: 30d)
- Middleware protects all routes except `/`, `/login`, `/signup`
- No ML labels shown in UI — confidence shown as "Clarity Indicator"
- Prescription status polling: 3s interval until analyzed/failed

### Database Models
- `users` — id, email, hashed_password, full_name, role, is_active
- `patients` — id, mrn, full_name, dob, age, gender, allergies, medications
- `prescriptions` — id, uploaded_by, patient_id, status, extracted_fields (JSONB), ocr_confidence
- `discrepancy_reports` — id, label, confidence, rule_label, llm_reason, evidence_sources (JSONB), pharmacist_label

### Discrepancy Labels
- `No Discrepancy` → green
- `Omission` → amber (missing info)
- `Commission` → red (incorrect entry)
- `Inconsistency` → orange (internal conflict)
- `Illegibility` → gray (unreadable)
