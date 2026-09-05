<div align="center">

# 🏛️ Legal Metrology Compliance Scanner

### OCR-Powered Compliance Verification for Packaged Commodities

**Smart • Automated • Rule-Based Legal Metrology Compliance**

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-Latest-green.svg)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18-blue.svg)](https://react.dev/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-14+-blue.svg)](https://www.postgresql.org/)
[![Cloudinary](https://img.shields.io/badge/Cloudinary-Image%20Storage-orange.svg)](https://cloudinary.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

</div>


## 📖 Overview

**LegalMetro** is an AI-assisted compliance verification system designed to analyze packaged commodity labels and identify potential violations of the **Legal Metrology (Packaged Commodities) Rules, 2011**.

The system allows inspectors and authorized users to upload product packaging images. The application validates the images, stores them securely in Cloudinary, extracts text using OCR, identifies important product information, and evaluates the extracted information using a deterministic compliance rule engine.

The final result provides a **compliance score, grade, rule-wise results, detected issues, and a downloadable compliance report**.

### 🔍 Core Workflow

```text
Product Image
      ↓
Image Validation
      ↓
Image Quality Assessment
      ↓
Cloudinary Storage
      ↓
OCR Processing
      ↓
Field Extraction
      ↓
Compliance Rule Engine
      ↓
Compliance Score
      ↓
Compliance Report
````

---

## ✨ Key Features

| Feature                        | Description                                                                                           |
| ------------------------------ | ----------------------------------------------------------------------------------------------------- |
| 🤖 **OCR Processing**          | Extracts text from product packaging using EasyOCR                                                    |
| 📝 **Field Extraction**        | Extracts MRP, net quantity, manufacturer, dates, batch number, consumer care details and other fields |
| ⚖️ **Rule-Based Compliance**   | Deterministic validators evaluate extracted information against configured Legal Metrology rules      |
| 📊 **Compliance Scoring**      | Generates a compliance score from 0–100                                                               |
| 🖼️ **Cloud Image Storage**    | Product images are stored using Cloudinary                                                            |
| 🔍 **Image Quality Detection** | Detects blurry, blank, low-quality and unusable images                                                |
| 🛡️ **Role-Based Access**      | Supports Admin, LMO and Inspector roles                                                               |
| 🔐 **JWT Authentication**      | Secure token-based authentication and authorization                                                   |
| 📄 **Compliance Reports**      | Generates downloadable compliance reports                                                             |
| 🗃️ **Analysis History**       | Stores previous product analyses and results                                                          |
| 🚦 **PASS / FAIL / REVIEW**    | Provides clear compliance status                                                                      |
| 🧪 **Automated Testing**       | Backend testing using Pytest                                                                          |

---

# 🧱 Tech Stack

| Layer                | Technology                   |
| -------------------- | ---------------------------- |
| **Backend**          | FastAPI, Python 3.11+        |
| **Frontend**         | React 18, Vite, React Router |
| **Database**         | PostgreSQL                   |
| **ORM**              | SQLAlchemy                   |
| **OCR**              | EasyOCR                      |
| **Image Processing** | OpenCV, Pillow               |
| **Image Storage**    | Cloudinary                   |
| **Authentication**   | JWT, Passlib, Bcrypt         |
| **Reports**          | jsPDF                        |
| **Testing**          | Pytest                       |
| **Package Manager**  | uv                           |

---

# 🚀 Quick Start

## Prerequisites

Install the following before running the project:

| Requirement | Version |
| ----------- | ------- |
| Python      | 3.11+   |
| Node.js     | 18+     |
| PostgreSQL  | 14+     |
| npm         | Latest  |
| uv          | Latest  |

Install `uv` from:

[https://docs.astral.sh/uv/](https://docs.astral.sh/uv/)

---

# 1️⃣ Clone the Repository

```bash
git clone https://github.com/Manojuio/LEGALMETRO.git
cd LEGALMETRO
```

---

# 2️⃣ Setup PostgreSQL

Create the application database:

```sql
CREATE DATABASE compliance_scanner;
```

Make sure PostgreSQL is running before starting the backend.

---

# 3️⃣ Configure Environment Variables

Create a `.env` file in the project root:

```env
DATABASE_HOST=localhost
DATABASE_PORT=5432
DATABASE_NAME=compliance_scanner
DATABASE_USER=postgres
DATABASE_PASSWORD=your_password

DEBUG=false

JWT_SECRET_KEY=change-this-in-production

CLOUDINARY_CLOUD_NAME=your_cloud_name
CLOUDINARY_API_KEY=your_api_key
CLOUDINARY_API_SECRET=your_api_secret
```

> ⚠️ **Never commit `.env` to GitHub.**

Cloudinary credentials are required for uploading product images.

---

# 4️⃣ Setup Backend

Create a Python virtual environment:

### Windows PowerShell

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install project dependencies:

```bash
uv sync
```

---

## Initialize Database Tables

Run:

```bash
python -c "from app.core.database import engine, Base; import app.models; Base.metadata.create_all(bind=engine); print('DATABASE TABLES CREATED SUCCESSFULLY')"
```

---

## Seed Compliance Rules

Load the configured compliance rules into PostgreSQL:

### Windows PowerShell

```powershell
$env:PYTHONPATH="."
python scripts\seed_db.py
```

The seeded rules are used by the compliance engine during analysis.

---

# 5️⃣ Start Backend

From the project root:

```bash
python -m uvicorn app.main:app --reload
```

The backend will run at:

```text
http://127.0.0.1:8000
```

### Swagger API Documentation

```text
http://127.0.0.1:8000/docs
```

### Health Check

```text
http://127.0.0.1:8000/api/v1/health/ready
```

---

# 6️⃣ Setup Frontend

Open a new terminal:

```bash
cd frontend
npm install
npm run dev
```

The frontend will run at:

```text
http://localhost:5173
```

---

# 🎯 How It Works

```text
┌──────────────────────┐
│    Product Image     │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│ Image Validation     │
│ • Size               │
│ • Format             │
│ • Dimensions         │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│ Image Quality        │
│ Assessment            │
│ • Blur               │
│ • Brightness         │
│ • Usability          │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│ Cloudinary Storage   │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│ OCR Processing       │
│ EasyOCR + OpenCV     │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│ Field Extraction     │
│                      │
│ MRP                  │
│ Net Quantity         │
│ Manufacturer         │
│ Consumer Care        │
│ Dates                │
│ Batch Number         │
│ Country of Origin    │
│ Unit Sale Price      │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│ Compliance Engine    │
│ Rule-Based Checks    │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│ Compliance Score     │
│       0 - 100        │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│ Compliance Report    │
└──────────────────────┘
```

---

# 🧠 OCR & Image Processing

LegalMetro uses **EasyOCR** together with OpenCV and Pillow for image processing and text extraction.

### Processing Pipeline

1. Upload product image
2. Validate file size
3. Validate image format
4. Validate image dimensions
5. Assess image quality
6. Preprocess image
7. Run OCR
8. Normalize detected text
9. Build OCR text blocks and lines
10. Extract important product fields
11. Evaluate extraction confidence
12. Run compliance rules
13. Calculate compliance score
14. Generate compliance result

### Supported Image Formats

```text
JPEG
PNG
WEBP
BMP
TIFF
```

### Maximum Upload Size

```text
100 MB
```

---

# ☁️ Cloudinary Image Storage

Product images are stored in **Cloudinary** instead of relying on local filesystem storage.

Images are organized using the analysis ID:

```text
legalmetrix/
│
└── analysis_<analysis_id>/
    ├── front
    ├── back
    ├── top
    ├── bottom
    └── other
```

The database stores the Cloudinary secure URL for each uploaded image.

Example:

```text
https://res.cloudinary.com/<cloud_name>/...
```

### Benefits

* Persistent cloud storage
* No dependency on local upload directories
* Easy image retrieval
* Suitable for cloud deployment
* Images can be accessed by the OCR pipeline through their URLs

---

# ⚖️ Compliance Rule Engine

The compliance engine is **deterministic and rule-based**.

The system does not rely on an LLM to make the final compliance decision.

Extracted product information is evaluated against configured Legal Metrology rules.

Rules are maintained in:

```text
rules/rules.json
```

Rules can be loaded into the database using:

```bash
python scripts/seed_db.py
```

### Example Compliance Fields

The system can evaluate fields such as:

* MRP
* Net Quantity
* Manufacturer Name
* Packer Details
* Consumer Care Information
* Manufacturing / Packing Date
* Expiry / Best Before
* Commodity Name
* Country of Origin
* Batch / Lot Number
* Unit Sale Price

---

# 📊 Compliance Scoring

The system generates an overall compliance score between **0 and 100**.

| Score Range | Grade | Status            | Meaning            |
| ----------: | :---: | ----------------- | ------------------ |
|      90–100 |   A+  | Excellent         | Fully Compliant    |
|       75–89 |   A   | Satisfactory      | Compliant          |
|       60–74 |   B   | Needs Improvement | Minor Issues       |
|       45–59 |   C   | Poor              | Significant Issues |
|       30–44 |   D   | Critical          | Non-Compliant      |
|        0–29 |   F   | Fail              | Non-Compliant      |

### Primary Fields

Important fields considered by the scoring system include:

* MRP
* Net Quantity
* Manufacturer Name
* Consumer Care Contact

### Supporting Fields

* Manufacturing Date
* Expiry / Best Before
* Commodity Name

### Additional Fields

* Country of Origin
* Batch Number
* Unit Sale Price

> ⚠️ Blank, unreadable or unusable images can result in very low compliance scores because no reliable information can be extracted.

---

# 🛡️ Roles & Permissions

| Role          | Permissions                                                 |
| ------------- | ----------------------------------------------------------- |
| **Admin**     | Manage users, access analyses and system-wide functionality |
| **LMO**       | Create products, upload images and run compliance analyses  |
| **Inspector** | Review analyses, inspections and compliance reports         |

Authentication and authorization are handled using JWT.

---

# 📄 Compliance Reports

The application generates downloadable compliance reports containing information such as:

* Product information
* Uploaded images
* Extracted fields
* OCR results
* Compliance rules
* Rule-wise results
* Detected issues
* Compliance score
* Grade
* Compliance status

Reports can be downloaded directly from the application.

---

# 🗃️ Analysis & Inspection History

Every analysis is stored in PostgreSQL.

The system maintains information related to:

* Analysis
* Product
* Uploaded images
* OCR results
* Extracted fields
* Compliance results
* Rule evaluations
* Inspection history

This allows users to review previous analyses and track compliance results.

---

# 📁 Project Structure

```text
LEGALMETRO/
│
├── app/
│   ├── api/
│   │   ├── auth.py
│   │   ├── analysis.py
│   │   └── ...
│   │
│   ├── compliance/
│   │   ├── ...
│   │
│   ├── models/
│   │   ├── analysis.py
│   │   └── ...
│   │
│   ├── services/
│   │   ├── analysis/
│   │   │   └── ocr_pipeline.py
│   │   │
│   │   ├── image/
│   │   │   └── validator.py
│   │   │
│   │   ├── ocr/
│   │   │   └── ...
│   │   │
│   │   └── extraction/
│   │       └── ...
│   │
│   └── core/
│       ├── config.py
│       └── database.py
│
├── frontend/
│   ├── src/
│   │   ├── pages/
│   │   ├── components/
│   │   └── utils/
│   │
│   └── package.json
│
├── rules/
│   └── rules.json
│
├── scripts/
│   ├── seed_db.py
│   ├── clear_db.py
│   └── evaluate_golden.py
│
├── tests/
│
├── main.py
├── pyproject.toml
├── uv.lock
├── README.md
└── .gitignore
```

---

# 🛠️ Utility Scripts

| Script                       | Purpose                                     |
| ---------------------------- | ------------------------------------------- |
| `scripts/seed_db.py`         | Seeds compliance rules into PostgreSQL      |
| `scripts/clear_db.py`        | Clears/reset database data                  |
| `scripts/evaluate_golden.py` | Evaluates extraction against golden samples |
| `test_images.py`             | Tests image processing functionality        |

---

# 🧪 Running Tests

From the project root:

```bash
python -m pytest
```

For verbose output:

```bash
python -m pytest -v
```

---

# 🔌 API Documentation

After starting the backend, open:

```text
http://127.0.0.1:8000/docs
```

FastAPI provides an interactive Swagger UI for testing and exploring the API.

---

# 🔐 Security

Sensitive configuration is stored using environment variables.

The following files and directories should **never be committed**:

```text
.env
.env.local
.env.production
.venv/
node_modules/
frontend/node_modules/
frontend/.next/
uploads/
reports/
debug/
```

Never expose:

* Database passwords
* JWT secret keys
* Cloudinary API keys
* Cloudinary API secrets

---

# 🚀 Deployment Architecture

The recommended production architecture is:

```text
                         ┌──────────────────┐
                         │     Frontend     │
                         │   React / Vite   │
                         │      Vercel      │
                         └────────┬─────────┘
                                  │
                                  │ HTTPS
                                  ▼
                         ┌──────────────────┐
                         │ FastAPI Backend  │
                         │                  │
                         │ EasyOCR          │
                         │ OpenCV           │
                         │ SQLAlchemy       │
                         │ JWT              │
                         └───────┬──────────┘
                                 │
                    ┌────────────┴────────────┐
                    │                         │
                    ▼                         ▼
          ┌──────────────────┐       ┌──────────────────┐
          │   PostgreSQL     │       │    Cloudinary    │
          │    Database      │       │ Image Storage    │
          └──────────────────┘       └──────────────────┘
```

### Recommended Deployment

| Component     | Platform           |
| ------------- | ------------------ |
| Frontend      | Vercel             |
| Backend       | Render / Railway   |
| Database      | Managed PostgreSQL |
| Image Storage | Cloudinary         |

> ⚠️ EasyOCR and PyTorch are CPU-intensive. The FastAPI backend should therefore run on a server/container environment rather than a frontend serverless function.

---

# 📈 Future Enhancements

Potential future improvements include:

* Advanced OCR optimization
* Multi-language OCR
* Improved field extraction
* More comprehensive Legal Metrology rules
* Mobile application
* Inspector dashboard
* Advanced analytics
* Batch product scanning
* Cloud-based report storage
* Notification system
* Improved image preprocessing
* AI-assisted issue explanations

---

# 🤝 Contributing

1. Create a new branch:

```bash
git checkout -b feature/my-feature
```

2. Make your changes.

3. Run tests:

```bash
python -m pytest
```

4. Commit your changes:

```bash
git add .
git commit -m "Add my feature"
```

5. Push the branch:

```bash
git push -u origin feature/my-feature
```

6. Open a Pull Request.

---

# 📜 License

MIT License — see [LICENSE](LICENSE) for details.

---

<div align="center">

## 🏛️ LegalMetro

### AI-Assisted Legal Metrology Compliance Verification

**Built for Smart India Hackathon (SIH)**

Made with ❤️ by the LegalMetro Team

</div>
```

