# AI-Powered Prescription Discrepancy Detection System
## Full Implementation Plan

---

## 1. System Architecture Overview

Five-layer pipeline:

```
DATA SOURCES → OCR/VISION (GPT-4o) → DATA VALIDATION → AI ANALYSIS → OUTPUT
```

### Layers

| Layer | Purpose | Key Tech |
|---|---|---|
| Data Sources | Prescription images, digital text, patient records | S3, FastAPI upload |
| Processing | OCR + structured extraction | OpenAI GPT-4o Vision |
| Validation | Drug DB checks | RxNorm, OpenFDA, DrugBank |
| AI Analysis | Classify discrepancy | GPT-4o + LangChain RAG + Rule Engine + XGBoost |
| Output | Dashboard + reports | React/Next.js, WeasyPrint PDF |

### AI Analysis — three parallel tracks

1. **RAG + LLM (GPT-4o)** — retrieves clinical guidelines from FAISS vector store, reasons about the prescription, classifies discrepancy type, cites evidence
2. **Rule Engine** — deterministic safety rules fire first; hard floor that cannot be overridden by AI
3. **ML Classifier (XGBoost)** — runs on structured features, provides confidence baseline; when it agrees with LLM → `consensus: HIGH`

---

## 2. Folder Structure

```
rx-discrepancy-detection/
├── backend/
│   ├── app/
│   │   ├── main.py                  # FastAPI entrypoint
│   │   ├── config.py                # Settings (env vars, secrets)
│   │   ├── dependencies.py          # JWT auth, DB sessions
│   │   │
│   │   ├── api/
│   │   │   └── v1/
│   │   │       ├── prescriptions.py # Upload, analyze, retrieve
│   │   │       ├── reports.py       # PDF generation, download
│   │   │       ├── patients.py      # Patient records
│   │   │       └── auth.py          # Login, token refresh
│   │   │
│   │   ├── services/
│   │   │   ├── ocr/
│   │   │   │   ├── vision_extractor.py  # GPT-4o Vision call
│   │   │   │   ├── text_cleaner.py      # Normalization, spelling
│   │   │   │   └── confidence.py        # OCR confidence scoring
│   │   │   │
│   │   │   ├── validation/
│   │   │   │   ├── rxnorm_client.py     # RxNorm API wrapper
│   │   │   │   ├── openfda_client.py    # OpenFDA wrapper
│   │   │   │   ├── drugbank.py          # DrugBank local/API
│   │   │   │   └── drug_validator.py    # Orchestrates all checks
│   │   │   │
│   │   │   ├── rag/
│   │   │   │   ├── embedder.py          # text-embedding-3-small
│   │   │   │   ├── vector_store.py      # FAISS index CRUD
│   │   │   │   ├── retriever.py         # Top-k similarity search
│   │   │   │   └── knowledge_loader.py  # Ingest guidelines/PubMed
│   │   │   │
│   │   │   ├── rules/
│   │   │   │   ├── engine.py            # Rule orchestrator
│   │   │   │   ├── omission_rules.py
│   │   │   │   ├── commission_rules.py
│   │   │   │   ├── consistency_rules.py
│   │   │   │   └── illegibility_rules.py
│   │   │   │
│   │   │   ├── llm/
│   │   │   │   ├── reasoning_chain.py   # LangChain chain
│   │   │   │   ├── prompts.py           # Prompt templates
│   │   │   │   └── classifier.py        # Discrepancy classifier
│   │   │   │
│   │   │   ├── ml/
│   │   │   │   ├── feature_extractor.py # Structured features
│   │   │   │   ├── predictor.py         # Load & run model
│   │   │   │   └── model/
│   │   │   │       └── xgboost_v1.pkl
│   │   │   │
│   │   │   ├── aggregator.py            # Merge rules + LLM + ML
│   │   │   └── report_generator.py      # PDF via WeasyPrint
│   │   │
│   │   ├── models/
│   │   │   ├── prescription.py          # SQLAlchemy ORM
│   │   │   ├── patient.py
│   │   │   ├── discrepancy_report.py
│   │   │   └── user.py
│   │   │
│   │   └── utils/
│   │       ├── s3.py                    # AWS S3 helpers
│   │       ├── redis_cache.py
│   │       └── logger.py
│   │
│   ├── tests/
│   │   ├── test_ocr.py
│   │   ├── test_rules.py
│   │   ├── test_rag.py
│   │   └── test_api.py
│   ├── Dockerfile
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   │   ├── pages/
│   │   │   ├── index.tsx           # Landing / login
│   │   │   ├── dashboard.tsx       # Prescription list
│   │   │   ├── upload.tsx          # Drag-drop uploader
│   │   │   ├── analysis/[id].tsx   # Result viewer
│   │   │   └── report/[id].tsx     # PDF report preview
│   │   │
│   │   ├── components/
│   │   │   ├── UploadZone.tsx
│   │   │   ├── FieldExtractPanel.tsx
│   │   │   ├── DiscrepancyBadge.tsx
│   │   │   ├── ConfidenceGauge.tsx
│   │   │   ├── EvidenceDrawer.tsx  # RAG citations slide-out
│   │   │   ├── MLCompare.tsx       # LLM vs ML side-by-side
│   │   │   └── ReportViewer.tsx
│   │   │
│   │   ├── hooks/
│   │   │   ├── usePrescription.ts
│   │   │   └── useAnalysis.ts
│   │   │
│   │   └── lib/
│   │       ├── api.ts              # Axios client
│   │       └── types.ts
│   │
│   ├── Dockerfile
│   └── package.json
│
├── ml/
│   ├── data/
│   │   ├── raw/                    # Original prescription images
│   │   ├── labeled/                # JSON ground truth
│   │   └── features/               # Extracted feature CSVs
│   │
│   ├── notebooks/
│   │   ├── 01_eda.ipynb
│   │   ├── 02_feature_eng.ipynb
│   │   └── 03_training.ipynb
│   │
│   ├── train.py                    # XGBoost training script
│   ├── evaluate.py                 # Metrics, confusion matrix
│   └── requirements.txt
│
├── infra/
│   ├── docker-compose.yml
│   ├── docker-compose.prod.yml
│   ├── nginx/
│   │   └── nginx.conf
│   └── k8s/                        # Optional Kubernetes manifests
│
└── .github/
    └── workflows/
        └── ci.yml
```

---

## 3. Backend API Routes

All routes prefixed `/api/v1`. JWT Bearer auth on all non-auth routes.

### Auth

| Method | Path | Description |
|---|---|---|
| POST | `/auth/login` | Returns JWT access + refresh token |
| POST | `/auth/refresh` | Exchange refresh token |
| DELETE | `/auth/logout` | Revoke token |

### Prescriptions

| Method | Path | Description |
|---|---|---|
| POST | `/prescriptions/upload` | Upload image/PDF → returns `prescription_id` + `job_id` |
| GET | `/prescriptions/` | List prescriptions (paginated, filterable) |
| GET | `/prescriptions/{id}` | Full prescription with extracted fields |
| DELETE | `/prescriptions/{id}` | Soft delete |

### Analysis

| Method | Path | Description |
|---|---|---|
| POST | `/analysis/run/{id}` | Trigger full pipeline (async) → `job_id` |
| GET | `/analysis/status/{job_id}` | Poll: `pending / running / done / failed` |
| GET | `/analysis/result/{id}` | Full result: label, confidence, evidence, ML prediction |
| PATCH | `/analysis/feedback/{id}` | Pharmacist correction → feeds active learning |

### Reports

| Method | Path | Description |
|---|---|---|
| POST | `/reports/generate/{id}` | Generate PDF discrepancy report |
| GET | `/reports/download/{id}` | Stream PDF (`Content-Disposition: attachment`) |

### Sample Response

```json
{
  "prescription_id": "rx_9a3f2b",
  "status": "complete",
  "extracted_fields": {
    "patient_name": "Ravi Kumar",
    "patient_age": 52,
    "drug_name": "Azithromycin",
    "dose": "500 mg",
    "frequency": "BD",
    "duration": "7 days",
    "diagnosis": "URTI",
    "doctor_name": "Dr. S. Mehta",
    "signature_present": true
  },
  "discrepancy": {
    "label": "Inconsistency",
    "confidence": 0.89,
    "rule_triggered": "frequency_inconsistent_with_guideline",
    "llm_reason": "Azithromycin is typically prescribed OD (once daily). BD (twice daily) is inconsistent with WHO guidelines.",
    "evidence_sources": [
      "WHO Essential Medicines List 2023 — Azithromycin dosing",
      "Medscape Drug Reference — Azithromycin adult dosing"
    ],
    "ml_prediction": {
      "label": "Inconsistency",
      "confidence": 0.81
    },
    "consensus": "HIGH",
    "flagged_fields": ["frequency"]
  }
}
```

---

## 4. Database Schema (PostgreSQL)

```sql
-- users
CREATE TABLE users (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email         TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role          TEXT CHECK (role IN ('pharmacist','admin','viewer')),
    created_at    TIMESTAMPTZ DEFAULT now()
);

-- patients
CREATE TABLE patients (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name        TEXT,
    age         INT,
    allergies   JSONB,
    medications JSONB,
    created_at  TIMESTAMPTZ DEFAULT now()
);

-- prescriptions
CREATE TABLE prescriptions (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id  UUID REFERENCES patients(id),
    uploaded_by UUID REFERENCES users(id),
    s3_key      TEXT NOT NULL,
    input_type  TEXT CHECK (input_type IN ('image','pdf','text')),
    status      TEXT DEFAULT 'pending',
    created_at  TIMESTAMPTZ DEFAULT now()
);

-- extracted_fields
CREATE TABLE extracted_fields (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    prescription_id   UUID REFERENCES prescriptions(id) ON DELETE CASCADE,
    patient_name      TEXT,
    patient_age       INT,
    drug_name         TEXT,
    dose              TEXT,
    frequency         TEXT,
    duration          TEXT,
    diagnosis         TEXT,
    doctor_name       TEXT,
    signature_present BOOLEAN,
    raw_ocr_json      JSONB,
    field_confidences JSONB,        -- {"dose": 0.91, "frequency": 0.54}
    extracted_at      TIMESTAMPTZ DEFAULT now()
);

-- discrepancy_reports
CREATE TABLE discrepancy_reports (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    prescription_id  UUID REFERENCES prescriptions(id) ON DELETE CASCADE,
    label            TEXT CHECK (label IN (
                       'No Discrepancy','Omission','Commission',
                       'Inconsistency','Illegibility')),
    confidence       FLOAT,
    rule_triggered   TEXT,
    llm_reason       TEXT,
    llm_evidence     JSONB,
    ml_prediction    TEXT,
    ml_confidence    FLOAT,
    consensus        TEXT CHECK (consensus IN ('HIGH','LOW')),
    flagged_fields   JSONB,
    pdf_s3_key       TEXT,
    reviewed_by      UUID REFERENCES users(id),
    correction_label TEXT,
    created_at       TIMESTAMPTZ DEFAULT now()
);

-- Indexes
CREATE INDEX idx_prescriptions_patient  ON prescriptions(patient_id);
CREATE INDEX idx_prescriptions_status   ON prescriptions(status);
CREATE INDEX idx_reports_label          ON discrepancy_reports(label);
CREATE INDEX idx_reports_consensus      ON discrepancy_reports(consensus);
```

### Redis Key Patterns

```
job:{job_id}                → JSON job status (TTL 24h)
cache:rxnorm:{drug_name}    → validated drug info (TTL 7d)
cache:openfda:{drug_name}   → FDA drug data (TTL 7d)
session:{user_id}           → JWT refresh metadata (TTL 30d)
```

---

## 5. OCR Pipeline (GPT-4o Vision)

### Flow

1. **Image ingestion** — Upload to S3. Validate MIME type and size (max 10MB). Store S3 key in Postgres.
2. **GPT-4o Vision call** — Send image + structured extraction prompt. Request JSON-only response. Use `logprobs=True` for per-field confidence.
3. **Text normalization** — Expand abbreviations (TDS → three times daily). Fuzzy-match drug names against dictionary. Normalize units (mcg ↔ µg).
4. **Confidence scoring** — Derive per-field confidence from logprobs. Fields below 0.60 → pre-flag as `Illegibility` before rules run.

### Pseudocode

```python
# services/ocr/vision_extractor.py

EXTRACTION_PROMPT = """
You are a medical data extraction system.
Extract ALL fields from this prescription image as JSON only.
If a field is missing or illegible, set value to null and
set "{field}_confidence": 0.0–0.3.

Required fields:
  patient_name, patient_age, drug_name, dose,
  frequency, duration, diagnosis, doctor_name, signature_present

Return ONLY valid JSON. No markdown, no explanation.
"""

async def extract_prescription(image_url: str) -> ExtractedFields:
    response = await openai.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": EXTRACTION_PROMPT},
            {"role": "user", "content": [
                {"type": "image_url", "image_url": {"url": image_url}},
                {"type": "text",      "text": "Extract all fields."}
            ]}
        ],
        response_format={"type": "json_object"},
        logprobs=True
    )
    raw = json.loads(response.choices[0].message.content)
    return normalize_and_score(raw, response.choices[0].logprobs)
```

---

## 6. RAG Pipeline

### Flow

1. **Knowledge ingestion (offline)** — Load WHO EML, BNF summaries, PubMed abstracts. Chunk at 512 tokens with 64-token overlap. Embed with `text-embedding-3-small`. Store in FAISS.
2. **Query construction** — `"{drug_name} {dose} {frequency} {diagnosis} prescribing guidelines dosage"`
3. **Top-k retrieval** — Retrieve 5 chunks by cosine similarity. Filter at score ≥ 0.72.
4. **LLM reasoning** — LangChain chain: system prompt + retrieved context + extracted JSON → classify + explain + cite sources.

### Pseudocode

```python
# services/llm/reasoning_chain.py

REASONING_PROMPT = """
You are a clinical pharmacist AI assistant.

RETRIEVED CLINICAL CONTEXT:
{context}

PRESCRIPTION:
{prescription_json}

Analyse this prescription for discrepancies.
Classify as one of:
  No Discrepancy | Omission | Commission | Inconsistency | Illegibility

Return JSON ONLY:
{
  "label": "...",
  "confidence": 0.0–1.0,
  "reason": "...",
  "flagged_fields": [...],
  "evidence_sources": [...]
}
"""

async def analyse(prescription: dict) -> DiscrepancyResult:
    query  = build_query(prescription)
    chunks = vector_store.similarity_search(query, k=5)
    context = "\n\n".join([c.page_content for c in chunks])

    chain  = LLMChain(
        llm=ChatOpenAI(model="gpt-4o"),
        prompt=PromptTemplate.from_template(REASONING_PROMPT)
    )
    result = await chain.arun(
        context=context,
        prescription_json=json.dumps(prescription)
    )
    return DiscrepancyResult(**json.loads(result))
```

---

## 7. Rule Engine

Rules fire **before** the LLM call. A triggered rule returns immediately and the label is final unless the pharmacist overrides it.

```python
# services/rules/engine.py

def run_rules(fields: dict,
              drug_info: dict,
              ocr_confidence: dict) -> RuleResult | None:

    # --- OMISSION ---
    for field in ["drug_name", "dose", "frequency", "duration"]:
        if not fields.get(field):
            return RuleResult(
                label="Omission",
                reason=f"Required field '{field}' is missing",
                flagged=[field],
                triggered_rule=f"missing_{field}"
            )

    # --- ILLEGIBILITY ---
    for field, conf in ocr_confidence.items():
        if conf < 0.60:
            return RuleResult(
                label="Illegibility",
                reason=f"Field '{field}' OCR confidence too low ({conf:.2f})",
                flagged=[field]
            )

    # --- COMMISSION: dose out of range ---
    dose_val = parse_dose(fields["dose"])
    if dose_val:
        lo = drug_info["dose_range"]["min"]
        hi = drug_info["dose_range"]["max"]
        if not lo <= dose_val <= hi:
            return RuleResult(
                label="Commission",
                reason=f"Dose {fields['dose']} outside safe range {lo}–{hi} mg",
                flagged=["dose"]
            )

    # --- INCONSISTENCY: drug interaction ---
    if drug_info.get("interaction_conflict"):
        return RuleResult(
            label="Inconsistency",
            reason=f"Drug interaction: {drug_info['interaction_detail']}",
            flagged=["drug_name"]
        )

    # --- INCONSISTENCY: diagnosis mismatch ---
    if fields.get("diagnosis") and drug_info.get("indications"):
        if fields["diagnosis"].lower() not in drug_info["indications"]:
            return RuleResult(
                label="Inconsistency",
                reason="Drug indication does not match stated diagnosis",
                flagged=["diagnosis", "drug_name"]
            )

    return None  # No rule triggered → pass to LLM + ML
```

---

## 8. ML Training Pipeline

### Features

```python
FEATURES = [
    "dose_present",           # bool
    "frequency_present",      # bool
    "duration_present",       # bool
    "diagnosis_present",      # bool
    "signature_present",      # bool
    "dose_in_valid_range",    # bool — from drug DB
    "valid_frequency_code",   # bool — OD/BD/TDS/QID/etc.
    "drug_interaction_flag",  # bool — from DrugBank
    "missing_fields_count",   # int 0–9
    "min_ocr_confidence",     # float
    "drug_name_valid",        # bool — from RxNorm
    "dose_form_match",        # bool
]

LABELS = [
    "No Discrepancy",
    "Omission",
    "Commission",
    "Inconsistency",
    "Illegibility"
]
```

### Training Script

```python
# ml/train.py

X, y = load_feature_dataset("ml/data/features/labeled.csv")
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, stratify=y)

model = XGBClassifier(
    n_estimators=200,
    max_depth=6,
    learning_rate=0.05,
    use_label_encoder=False,
    eval_metric="mlogloss"
)
model.fit(X_train, y_train,
          eval_set=[(X_test, y_test)],
          early_stopping_rounds=20)

# Evaluation
print(classification_report(y_test, model.predict(X_test)))

# SHAP explainability
explainer  = shap.TreeExplainer(model)
shap_values = explainer.shap_values(X_test)
shap.summary_plot(shap_values, X_test, feature_names=FEATURES)

# Export
joblib.dump(model, "backend/app/services/ml/model/xgboost_v1.pkl")
```

---

## 9. Aggregator (Rules + LLM + ML → Final)

```python
# services/aggregator.py

def aggregate(
    rule_result:  RuleResult | None,
    llm_result:   DiscrepancyResult,
    ml_result:    MLPrediction
) -> FinalResult:

    # Rule engine is authoritative — cannot be overridden by AI
    if rule_result:
        return FinalResult(
            label=rule_result.label,
            confidence=1.0,
            source="rule_engine",
            consensus="HIGH",
            llm_result=llm_result,
            ml_result=ml_result
        )

    # Compare LLM and ML
    consensus = "HIGH" if llm_result.label == ml_result.label else "LOW"

    # Average confidence when they agree; use LLM confidence when they don't
    if consensus == "HIGH":
        confidence = round((llm_result.confidence + ml_result.confidence) / 2, 3)
    else:
        confidence = llm_result.confidence   # LLM is primary

    return FinalResult(
        label=llm_result.label,
        confidence=confidence,
        source="llm_rag",
        consensus=consensus,
        llm_result=llm_result,
        ml_result=ml_result,
        needs_review=(consensus == "LOW")
    )
```

---

## 10. Frontend Component Structure

### Pages (Next.js App Router)

| Route | Component | Purpose |
|---|---|---|
| `/dashboard` | `DashboardPage` | Prescription list, status pills, filter bar |
| `/upload` | `UploadPage` | Drag-drop zone, camera capture, text input |
| `/analysis/[id]` | `AnalysisPage` | Result view with all panels |
| `/report/[id]` | `ReportPage` | PDF preview + download |

### Key Components

**`UploadZone.tsx`** — React Dropzone. Accepts jpg/png/pdf. Shows preview thumbnail. POSTs to `/prescriptions/upload`, polls job status, redirects to `/analysis/[id]` on completion.

**`FieldExtractPanel.tsx`** — Table of extracted fields. Flagged fields highlighted amber. Per-field confidence shown as a thin progress bar beneath the value.

**`DiscrepancyBadge.tsx`** — Colored pill: Omission=amber, Commission=red, Inconsistency=orange, Illegibility=gray, No Discrepancy=green.

**`EvidenceDrawer.tsx`** — Slide-out right panel listing the RAG-retrieved guideline chunks used by the LLM. Each chunk shows source name, excerpt, and similarity score.

**`MLCompare.tsx`** — Side-by-side card: LLM prediction vs ML prediction. Consensus indicator (`HIGH` / `LOW`). SHAP top-3 features for ML decision.

**`ConfidenceGauge.tsx`** — Radial gauge 0–100%. Green ≥ 80%, amber 60–79%, red < 60%.

### State / Data Flow

```
Upload image
  → POST /prescriptions/upload  → { prescription_id, job_id }
  → POST /analysis/run/{id}     → { job_id }
  → Poll GET /analysis/status/{job_id} every 2s
  → On status == "done"
      → GET /analysis/result/{id}
      → Render FieldExtractPanel + DiscrepancyBadge + EvidenceDrawer + MLCompare
  → Pharmacist clicks "Flag as incorrect"
      → PATCH /analysis/feedback/{id}
  → Pharmacist clicks "Generate Report"
      → POST /reports/generate/{id}
      → GET  /reports/download/{id}  → PDF download
```

---

## 11. Docker Setup

### `docker-compose.yml` (development)

```yaml
version: "3.9"
services:
  backend:
    build: ./backend
    ports: ["8000:8000"]
    env_file: .env
    depends_on: [postgres, redis]
    volumes: ["./backend:/app"]

  frontend:
    build: ./frontend
    ports: ["3000:3000"]
    environment:
      NEXT_PUBLIC_API_URL: http://localhost:8000/api/v1

  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: rxdetect
      POSTGRES_USER: rxuser
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes: ["pgdata:/var/lib/postgresql/data"]

  redis:
    image: redis:7-alpine
    ports: ["6379:6379"]

  celery_worker:
    build: ./backend
    command: celery -A app.worker worker --loglevel=info -Q analysis
    env_file: .env
    depends_on: [redis, postgres]

  nginx:
    image: nginx:alpine
    ports: ["80:80"]
    volumes: ["./infra/nginx/nginx.conf:/etc/nginx/conf.d/default.conf"]
    depends_on: [backend, frontend]

volumes:
  pgdata:
```

### `backend/Dockerfile`

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### `.env`

```
OPENAI_API_KEY=sk-...
DATABASE_URL=postgresql://rxuser:pass@postgres:5432/rxdetect
REDIS_URL=redis://redis:6379/0
AWS_S3_BUCKET=rx-images-prod
AWS_REGION=ap-south-1
JWT_SECRET_KEY=<32-byte-secret>
RXNORM_BASE_URL=https://rxnav.nlm.nih.gov/REST
OPENFDA_BASE_URL=https://api.fda.gov/drug
CELERY_BROKER_URL=redis://redis:6379/1
```

---

## 12. CI/CD Pipeline

```yaml
# .github/workflows/ci.yml
on: [push, pull_request]

jobs:
  test-backend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.11" }
      - run: pip install -r backend/requirements.txt
      - run: pytest backend/tests/ --cov=app --cov-report=xml

  test-frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: "20" }
      - run: cd frontend && npm ci && npm run lint && npm run build

  docker-build:
    needs: [test-backend, test-frontend]
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: docker compose build
```

---

## 13. Deployment Steps (AWS)

1. **RDS** — Provision PostgreSQL 16 instance in private subnet. Run Alembic migrations.
2. **ElastiCache** — Redis cluster for job queue and API cache.
3. **S3** — Bucket for prescription images. Enable server-side encryption (AES-256). Set lifecycle policy: delete after 30 days.
4. **ECR** — Push backend and frontend Docker images.
5. **ECS Fargate** — Services: `api` (backend), `worker` (Celery), `frontend`. Configure auto-scaling on CPU utilization.
6. **ALB** — Application Load Balancer. HTTP → HTTPS redirect. ACM certificate.
7. **Secrets Manager** — Store all secrets from `.env`. Reference in ECS task definitions.
8. **CloudWatch** — Log groups for each service. Alarms on 5xx rate > 1% and job queue depth > 100.

---

## 14. Development Timeline

| Week | Milestone |
|---|---|
| 1–2 | Project scaffold, Docker, Postgres schema, FastAPI skeleton, JWT auth, S3 upload, CI pipeline |
| 3–4 | GPT-4o Vision integration, structured JSON extraction, text normalization, confidence scoring, OCR unit tests |
| 5 | RxNorm + OpenFDA + DrugBank clients, dose/form/interaction checks, Redis caching |
| 6 | Full rule engine — all 5 discrepancy types, integration tests, audit logging |
| 7–8 | Knowledge ingestion, FAISS index, LangChain RAG chain, prompt tuning, evidence citation, aggregator |
| 9 | Feature extraction, XGBoost training, SHAP explainability, confidence aggregation, benchmarking report |
| 10 | Frontend — upload zone, dashboard, analysis page, EvidenceDrawer, MLCompare, PDF viewer |
| 11 | End-to-end integration, Celery async queue, feedback endpoint, performance profiling, cache tuning |
| 12 | HTTPS, rate limiting, audit logs, staging deploy to AWS, load testing, documentation, pilot pharmacy |

---

## 15. Scalability Considerations

- **Celery workers** for analysis jobs scale out independently from the API — add workers as queue depth grows
- **FAISS** can be swapped for **Pinecone** (managed) when the knowledge corpus exceeds ~500k vectors
- **Redis** caches all RxNorm/OpenFDA responses (7-day TTL) — repeat drug names skip external API calls entirely
- **GPT-4o batch API** can process high-volume queues at 50% cost reduction
- **Read replicas** on RDS for reporting queries; primary for writes only
- **CDN** (CloudFront) in front of S3 for frequently accessed prescription images

---

## 16. Security & HIPAA-Style Compliance

| Area | Implementation |
|---|---|
| Encryption at rest | pgcrypto for PHI columns; S3 AES-256 SSE |
| Encryption in transit | TLS 1.3 enforced end-to-end |
| Authentication | JWT 15-min access + 30-day rotating refresh; bcrypt cost 12 |
| Authorization | RBAC: pharmacist / admin / viewer |
| PHI minimization | Images deleted from S3 after 30 days; no raw PHI in logs |
| Audit trail | Immutable append-only log of all analysis runs and downloads |
| API security | Rate limiting 100 req/min; CORS locked; Pydantic validation; SQLAlchemy ORM (no raw SQL) |
| OpenAI data privacy | Use Azure OpenAI Service for full data residency; sign BAA on Enterprise plan |
| Future certifications | SOC 2 Type II; FDA SaMD (Software as a Medical Device) guidelines |

---

## 17. Future Improvement Roadmap

- **EHR / FHIR integration** — check prescriptions as doctors write them, not just at pharmacy
- **HL7 v2 messaging** — connect with hospital information systems
- **Patient allergy cross-check** — pull active allergies from patient record before analysis
- **Multi-language OCR** — Hindi, Tamil, Arabic prescription support
- **Mobile AR scanning** — live camera with real-time field highlighting
- **Voice order transcription** — Whisper API for verbal prescription orders
- **Generic substitution suggestions** — flag expensive branded drugs with bioequivalent generics
- **Active learning retraining** — pharmacist corrections feed back into XGBoost retraining pipeline monthly
- **SaaS multi-tenant billing** — tiered plans (Basic / Pro / Enterprise) per pharmacy / hospital chain

---

*Generated for: AI-Powered Prescription Discrepancy Detection System*
*Stack: FastAPI · Next.js · OpenAI GPT-4o · LangChain · FAISS · XGBoost · PostgreSQL · Redis · AWS*
