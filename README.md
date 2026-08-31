# LegalMetro — Packaged Commodities Compliance Scanner

A **local** web application that analyzes photographs of packaged commodities and checks them for compliance with India's **Legal Metrology (Packaged Commodities) Rules, 2011**.

> **LegalMetro** is a prototype built for the Smart India Hackathon. It is a compliance **scanner and decision-support tool** — it does **not** perform physical weighing/testing and does **not** issue legal certification.

## What it does

A user uploads photos of a product's packaging (front / back / side).

```
Image → Preprocess → OCR → Extract structured info → Classify product
     → Determine applicable rules → Run deterministic compliance checks
     → Run visual/CV checks → Generate evidence → PASS / FAIL / REVIEW
```

**Core principle:** OCR/CV are *evidence providers*. The **rule engine** makes the compliance decision using deterministic, auditable logic. No LLM is used for legal reasoning.

## Tech stack

| Layer | Technology |
|-------|-----------|
| Frontend | React + Vite (planned) |
| Backend | FastAPI (single backend — no Node.js) |
| ORM | SQLAlchemy 2.x |
| Validation | Pydantic / Pydantic Settings |
| Database | PostgreSQL |
| Auth | JWT (python-jose) + bcrypt |
| OCR | EasyOCR |
| Image | OpenCV + Pillow |
| PDF | ReportLab (planned) |
| Testing | Pytest + FastAPI TestClient |

## Project status

Phases 1–5 complete:

- **Phase 1–2:** Project specification + legal rule registry (`rules/`)
- **Phase 3–4:** High/low-level design + database schema (`docs/`)
- **Phase 5:** FastAPI foundation — health endpoints, all 12 SQLAlchemy models, seeded demo data

See `docs/PHASE_STATUS.md` and `docs/AI_CHANGELOG.md` for full details.

## Getting started

### Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) (or pip)
- Local PostgreSQL running on port 5432

### Setup

```bash
# 1. Install dependencies
uv sync

# 2. Configure database connection
#    Copy the values below into a `.env` file (gitignored):
#    DATABASE_HOST=localhost
#    DATABASE_PORT=5432
#    DATABASE_NAME=compliance_scanner
#    DATABASE_USER=postgres
#    DATABASE_PASSWORD=your_password

# 3. Create the database
psql -U postgres -c "CREATE DATABASE compliance_scanner;"

# 4. Seed demo data (5 users, 17 rules, 2 products, 2 analyses)
python -m scripts.seed_db

# 5. Run tests
pytest

# 6. Start the server
uvicorn app.main:app --reload
```

### Demo users (created by the seed script)

| Role | Email | Password |
|------|-------|----------|
| ADMIN | admin@example.com | admin123 |
| LMO | lmo@example.com | lmo123 |
| MANUFACTURER | manufacturer@example.com | mfr123 |
| RETAILER | retailer@example.com | retail123 |
| CONSUMER | consumer@example.com | consumer123 |

### Health endpoints

- `GET /health`
- `GET /api/v1/health`
- `GET /api/v1/health/ready` (checks DB connectivity)
- `GET /api/v1/version`

Interactive API docs: `http://localhost:8000/docs`

## Documentation

- `docs/ARCHITECTURE.md` — system design
- `docs/LLD.md` — database schema
- `docs/API.md` — endpoint documentation
- `docs/ROLES.md` — roles and access matrix
- `docs/RULE_SCOPE.md` — rule scope and automation levels
- `docs/DATA_FLOW.md` — data flows (upload → OCR → compliance)
- `docs/DECISIONS.md` — architectural decisions (AD-001+)
- `docs/AI_CHANGELOG.md` — every AI-assisted change (auditable)
- `docs/PHASE_STATUS.md` — phase-by-phase status

## License

Prototype for educational/demonstration purposes.
