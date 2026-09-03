<div align="center">

# 🏛️ Legal Metrology Compliance Scanner

### OCR-Powered Compliance Verification for Packaged Commodities

**Smart • Automated • Legal Metrology (Packaged Commodities) Rules, 2011**

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.14+-green.svg)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18-blue.svg)](https://react.dev)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-14+-blue.svg)](https://postgresql.org)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

</div>

---

## 📖 Overview

**LegalMetro** is an AI-powered compliance scanner that uses **OCR technology** to analyze product packaging images and automatically verify whether they comply with the **Legal Metrology (Packaged Commodities) Rules, 2011**.

Take a photo of any packaged product → the system extracts critical details like **MRP, Net Quantity, Manufacturer, Consumer Care Details** → runs **17 compliance rules** → generates a **professional compliance report** with an overall score.

---

## ✨ Key Features

| Feature | Description |
|---------|-------------|
| 🤖 **OCR Engine** | EasyOCR + Tesseract with advanced image preprocessing (denoise, deskew, quality assessment) |
| 📝 **Field Extraction** | Automatically extracts MRP, net quantity, manufacturer name, dates, batch numbers & more |
| ⚖️ **Rule Engine** | 17 Legal Metrology rules with deterministic validators — 100% automated, no LLM guesswork |
| 📊 **Smart Scoring** | Compliance score 0-100 with grade (A+ to F) and priority breakdown |
| 📄 **PDF Reports** | Professional compliance reports generated directly in the frontend, downloadable with one click |
| 🛡️ **Role-Based Access** | Admin, LMO & Inspector roles with granular permissions |
| 🖼️ **Image Quality Check** | Automatically detects blank/blurred/unusable images — they get a failing score |
| 🎯 **Real-time Feedback** | Animated score bars, instant PASS / FAIL / REVIEW status |

---

## 🚀 Quick Start

### Prerequisites

| Requirement | Version |
|-------------|---------|
| Python | 3.11+ |
| Node.js | 18+ |
| PostgreSQL | 14+ |
| uv (package manager) | Latest — [install here](https://docs.astral.sh/uv/) |

---

### 1️⃣ Clone the Repository

```bash
git clone https://github.com/Manojuio/LEGALMETRO.git
cd LEGALMETRO
```

### 2️⃣ Setup PostgreSQL

```sql
CREATE DATABASE compliance_scanner;
```

### 3️⃣ Configure Environment

Create a `.env` file in the project root:

```env
DATABASE_HOST=localhost
DATABASE_PORT=5432
DATABASE_NAME=compliance_scanner
DATABASE_USER=postgres
DATABASE_PASSWORD=your_password
DEBUG=false
JWT_SECRET_KEY=dev-secret-change-in-production
```

### 4️⃣ Setup Backend

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

> ✅ Backend runs at **http://127.0.0.1:8000**

### 5️⃣ Setup Frontend

```bash
cd frontend
npm install
npm run dev
```

> ✅ Frontend runs at **http://localhost:5173**

---

## 🎯 How It Works

```
┌─────────┐    ┌────────────┐    ┌──────────────┐    ┌─────────────┐
│ Product │ →  │ Image      │ →  │ OCR & Field  │ →  │ Rule Engine  │
│ Photo   │    │ Quality    │    │ Extraction   │    │ (17 rules)   │
└─────────┘    └────────────┘    └──────────────┘    └──────┬──────┘
                                                            │
                                                            ▼
                    ┌─────────────────┐    ┌──────────────┐
                    │  PDF Report     │ ←  │ Compliance   │
                    │  (Downloadable) │    │  Score 0-100 │
                    └─────────────────┘    └──────────────┘
```

---

## 📊 Scoring System

| Score Range | Grade | Status | Meaning |
|-------------|-------|--------|---------|
| 90 - 100 | 🟢 **A+** | Excellent | Fully Compliant |
| 75 - 89 | 🟢 **A** | Satisfactory | Compliant |
| 60 - 74 | 🟡 **B** | Needs Improvement | Minor Issues |
| 45 - 59 | 🟠 **C** | Poor | Significant Issues |
| 30 - 44 | 🔴 **D** | Critical | Non-Compliant |
| 0 - 29 | 🔴 **F** | Fail | Non-Compliant |

### Score Drivers
- **Key Fields** (4): MRP, Net Quantity, Manufacturer Name, Consumer Care Contact — each worth 25%
- **Supporting** (3): Manufacturing Date, Expiry, Commodity Name
- **Extra** (3): Country of Origin, Batch Number, Unit Sale Price

> ⚠️ **Blank or unreadable images automatically fail** — no fields detected = very low score.

---

## 🧱 Tech Stack

| Layer | Technology |
|-------|------------|
| **Backend** | FastAPI, SQLAlchemy, Python 3.11 |
| **Frontend** | React 18, Vite, React Router |
| **Database** | PostgreSQL |
| **OCR** | EasyOCR, OpenCV, Tesseract |
| **Auth** | JWT, Passlib, Bcrypt |
| **Reports** | jsPDF (frontend) |
| **Tests** | Pytest |

---

## 📁 Project Structure

```
LEGALMETRO/
├── app/
│   ├── api/               # API routes (auth, analysis, products)
│   ├── compliance/        # Rule engine, scoring engine, validators
│   ├── models/            # SQLAlchemy database models
│   ├── services/          # OCR pipeline, image processing, extraction
│   │   ├── analysis/      # OCR pipeline orchestration
│   │   ├── image/         # Quality assessment, preprocessing
│   │   ├── ocr/          # OCR engine integration
│   │   └── extraction/    # Field extraction, confidence scoring
│   └── core/              # Configuration, database setup
├── frontend/
│   └── src/
│       ├── pages/         # React pages (Dashboard, Analysis, etc.)
│       ├── components/    # Reusable UI components
│       └── utils/         # PDF generator, helpers
├── rules/
│   └── rules.json         # 17 Legal Metrology compliance rules
├── scripts/               # Utility scripts (clear_db, evaluation)
└── tests/                 # Automated backend tests
```

---

## 🛠️ Utility Scripts

| Script | Usage |
|--------|-------|
| `scripts/clear_db.py` | Reset database to clean state |
| `scripts/evaluate_golden.py` | Evaluate extraction accuracy against golden samples |

---

## 📚 API Documentation

Once the backend is running, access the interactive Swagger UI:

```
http://127.0.0.1:8000/docs
```

---

## 👥 Roles & Permissions

| Role | Permissions |
|------|-------------|
| **Admin** | Full access, manage users, view all analyses |
| **LMO** | Create products, run analyses, field inspections |
| **Inspector** | Review analyses & reports |

---

## 🧪 Running Tests

```bash
python -m pytest
```

---

## 📝 License

MIT License — see [LICENSE](LICENSE) for details.

---

<div align="center">

**Made with ❤️ for the Smart India Hackathon (SIH)**

</div>
