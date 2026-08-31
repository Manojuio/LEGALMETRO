# Architecture

## System Overview

The Packaged Commodities Compliance Scanner is a local web application built with a single FastAPI backend serving a React frontend. The system analyzes product packaging images to determine compliance with Legal Metrology (Packaged Commodities) Rules, 2011.

## Architecture Diagram

```
                    ┌─────────────────────┐
                    │     React/Vite       │
                    │    Interactive UI    │
                    └──────────┬──────────┘
                               │ HTTP/JSON
                               ▼
                    ┌─────────────────────┐
                    │       FastAPI       │
                    │   Main Application   │
                    ├─────────────────────┤
                    │ Auth + RBAC          │
                    │ Product Management   │
                    │ OCR Orchestration    │
                    │ Rule Engine          │
                    │ Compliance Engine    │
                    │ Report Generation    │
                    └──────────┬──────────┘
                               │
              ┌────────────────┼─────────────────┐
              ▼                ▼                 ▼
        PostgreSQL          EasyOCR          OpenCV/PIL
          Local DB         OCR engine       Image analysis
              │
              ▼
       Local image/files
```

## Component Responsibilities

### Frontend (React + Vite)

- User interface for all user interactions
- Image upload with preview
- Analysis results display
- Report viewing and download
- Role-specific dashboards
- Form handling and validation

### FastAPI Backend

Single application server handling:

- **Authentication**: JWT-based auth with role-based access control
- **API Routing**: RESTful endpoints for all operations
- **Business Logic**: Orchestration of compliance pipeline
- **Data Management**: CRUD operations via SQLAlchemy
- **File Management**: Image upload and storage

### Database (PostgreSQL)

- User accounts and roles
- Product metadata
- Analysis records
- OCR results
- Extracted fields
- Rule definitions and results
- Inspection records
- Audit logs

### OCR Engine (EasyOCR)

- Text extraction from images
- Confidence scoring
- Bounding box detection
- Local processing (no external APIs)

### Image Processing (OpenCV + Pillow)

- Image validation
- Preprocessing (resize, denoise, contrast)
- Font size estimation
- Contrast measurement
- Text placement analysis

### Rule Engine (Pure Python)

- Deterministic rule validation
- Applicability determination
- Exemption checking
- Evidence aggregation

## Why FastAPI as Sole Backend

### Reasoning

1. **Python Integration**: OCR (EasyOCR), CV (OpenCV), and rule engine are all Python. A single Python backend avoids cross-language serialization.

2. **Local Prototype**: No need for separate services when everything runs on one machine.

3. **Simplified Deployment**: One process to start, one port to expose.

4. **Pydantic Integration**: Built-in request/response validation without additional libraries.

5. **Async Support**: FastAPI handles async operations natively for concurrent image processing.

6. **OpenAPI Docs**: Automatic API documentation for the prototype.

### Why NOT Node.js + Express

- Would require Python child processes for OCR/CV
- Cross-language data transfer overhead
- Additional service to maintain
- No benefit for local prototype
- Complexity without value

## Request Flow

### Standard API Request

```
Client Request
    │
    ▼
CORS Middleware
    │
    ▼
Route Handler
    │
    ▼
Authentication Dependency
    │
    ▼
Role-Based Access Check
    │
    ▼
Business Logic (Service)
    │
    ▼
Database Query (SQLAlchemy)
    │
    ▼
Response (Pydantic Schema)
    │
    ▼
Client Response
```

### Analysis Pipeline Request

```
POST /api/v1/analyses/{id}/run
    │
    ▼
Load Analysis + Images
    │
    ▼
Image Validation
    │
    ▼
Image Preprocessing (OpenCV/Pillow)
    │
    ▼
OCR Processing (EasyOCR)
    │
    ▼
Information Extraction (Regex + Patterns)
    │
    ▼
Product Classification
    │
    ▼
Applicability Determination
    │
    ▼
Exemption Check
    │
    ▼
Rule Validation (Deterministic)
    │
    ▼
Visual/CV Checks
    │
    ▼
Result Aggregation
    │
    ▼
Evidence Generation
    │
    ▼
Database Persistence
    │
    ▼
Response with Results
```

## Authentication Flow

```
Login Request
    │
    ▼
Validate Credentials
    │
    ▼
Check Password (Argon2)
    │
    ▼
Generate JWT Token
    │
    ▼
Return Token + User Info
    │
    ▼
Client Stores Token
    │
    ▼
Subsequent Requests include Authorization: Bearer <token>
    │
    ▼
JWT Verification Middleware
    │
    ▼
Role-Based Access Check
    │
    ▼
Endpoint Access Granted/Denied
```

## Error Handling Flow

```
Request Processing
    │
    ├── Validation Error → 422 Unprocessable Entity
    │
    ├── Authentication Error → 401 Unauthorized
    │
    ├── Authorization Error → 403 Forbidden
    │
    ├── Not Found → 404 Not Found
    │
    ├── Business Logic Error → 400 Bad Request
    │
    └── Server Error → 500 Internal Server Error
```

## Data Flow

### Image to Compliance Result

```
Image File
    │
    ▼
Save to uploads/analysis_{id}/
    │
    ▼
Preprocessed Image
    │
    ▼
OCR Text + Bounding Boxes
    │
    ▼
Extracted Fields (MRP, quantity, etc.)
    │
    ▼
Product Category
    │
    ▼
Applicable Rules
    │
    ▼
Per-Rule Results (PASS/FAIL/REVIEW/NOT_APPLICABLE)
    │
    ▼
Overall Status
    │
    ▼
Evidence for Each Result
```

## Security Considerations

### Authentication

- JWT tokens with configurable expiry
- Argon2 password hashing (or bcrypt)
- Token-based stateless auth

### Authorization

- Role-based access via FastAPI dependencies
- Centralized role checking (no scattered if-else)
- Endpoint-level access control

### File Security

- File type validation on upload
- File size limits
- Filename sanitization
- Isolated upload directories

### Database Security

- Parameterized queries via SQLAlchemy
- No raw SQL injection vectors
- Connection pooling

## Scalability Notes

This is a local prototype. For production:

- Add Redis for caching
- Add Celery for background tasks
- Add nginx as reverse proxy
- Add TLS/SSL
- Add rate limiting
- Add request logging
- Add monitoring

## Technology Stack

| Layer | Technology | Version |
|-------|-----------|---------|
| Frontend | React + Vite | Latest |
| Styling | Tailwind CSS | Latest |
| Backend | FastAPI | 0.104+ |
| ORM | SQLAlchemy | 2.0+ |
| Validation | Pydantic | 2.0+ |
| Database | PostgreSQL | 14+ |
| Auth | PyJWT + Argon2 | Latest |
| OCR | EasyOCR | 1.7+ |
| Image | OpenCV + Pillow | Latest |
| PDF | ReportLab | Latest |
| Testing | Pytest | Latest |
| Migrations | Alembic | Latest |
