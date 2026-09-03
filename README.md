# Legal Metrology - Packaged Commodities Compliance Scanner

OCR-based compliance scanner for Legal Metrology (Packaged Commodities) Rules, 2011.

## Prerequisites

- **Python 3.11+**
- **Node.js 18+**
- **PostgreSQL 14+**
- **uv** (Python package manager) — install from https://docs.astral.sh/uv/

## Quick Start

### 1. Clone the repo

```bash
git clone https://github.com/Manojuio/LEGALMETRO.git
cd LEGALMETRO
```

### 2. Setup PostgreSQL

Create a database:

```sql
CREATE DATABASE compliance_scanner;
```

### 3. Configure environment

Create a `.env` file in the project root:

```
DATABASE_HOST=localhost
DATABASE_PORT=5432
DATABASE_NAME=compliance_scanner
DATABASE_USER=postgres
DATABASE_PASSWORD=your_password
DEBUG=false
JWT_SECRET_KEY=dev-secret-change-in-production
```

### 4. Setup Backend

```bash
uv sync
```

Initialize the database:

```bash
python -c "from app.database import engine, Base; Base.metadata.create_all(bind=engine)"
```

Seed an admin user:

```bash
python -m app.auth.seed
```

Start the backend:

```bash
uvicorn app.main:app --reload
```

Backend runs at http://127.0.0.1:8000

### 5. Setup Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend runs at http://localhost:5173

### 6. Login

- **Admin**: Register at http://localhost:5173/register or use seeded admin
- **LMO**: Create an LMO account from the admin panel

## Project Structure

```
LEGALMETRO/
├── app/
│   ├── api/            # API routes (auth, analysis, products)
│   ├── compliance/     # Rule engine, scoring, validators
│   ├── models/         # SQLAlchemy models
│   ├── services/       # OCR, extraction, image processing
│   └── core/           # Config, database setup
├── frontend/
│   └── src/
│       ├── pages/      # React pages (Dashboard, Analysis, etc.)
│       ├── components/ # Reusable UI components
│       └── utils/      # PDF generator, helpers
├── rules/
│   └── rules.json      # Legal Metrology compliance rules
├── scripts/            # Utility scripts (clear_db, seed, etc.)
└── tests/              # Backend tests
```

## Key Features

- **OCR Processing**: EasyOCR + Tesseract with image preprocessing
- **Field Extraction**: MRP, quantity, manufacturer, dates, etc.
- **Compliance Scoring**: 4 key parameters + 6 supporting checks
- **Rule Engine**: 17 Legal Metrology rules with automated validation
- **PDF Reports**: Professional compliance reports (frontend-generated)
- **Role-Based Access**: Admin, LMO, Inspector roles

## Scoring

| Score | Grade | Status |
|-------|-------|--------|
| 90+ | A+ | Excellent |
| 75-89 | A | Satisfactory |
| 60-74 | B | Needs Improvement |
| 45-59 | C | Poor |
| 30-44 | D | Critical |
| <30 | F | Fail |

## Reset Database

```bash
python scripts/clear_db.py
```

## API Documentation

Once running, visit http://127.0.0.1:8000/docs for the Swagger UI.
