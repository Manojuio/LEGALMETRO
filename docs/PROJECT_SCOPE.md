# Project Scope

## Packaged Commodities Compliance Scanner

### Problem Statement

India's Legal Metrology (Packaged Commodities) Rules, 2011 mandate specific labeling requirements on all pre-packaged commodities sold in the country. Manufacturers, retailers, and enforcement officers currently rely on manual inspection to verify compliance — a process that is slow, inconsistent, and unscalable.

There is no accessible tool that can:
- Automatically analyze product packaging images for labeling compliance
- Map detected information to specific legal rules
- Generate evidence-backed compliance reports
- Support multiple stakeholder roles (manufacturer, retailer, enforcement officer)

### Solution

A local web application that:
1. Accepts photographs of packaged commodity labels (front, back, side)
2. Uses OCR to extract text and metadata from images
3. Structures the extracted data into product information
4. Applies a deterministic rule engine against Legal Metrology rules
5. Generates compliance reports with evidence and confidence scores
6. Supports role-based access for different stakeholders

### Users

| Role | Purpose |
|------|---------|
| ADMIN | System management, rule configuration, user management |
| LMO (Legal Metrology Officer) | Product inspection, enforcement, report generation |
| MANUFACTURER | Pre-launch compliance verification, product management |
| RETAILER | Product scanning, MRP verification, compliance checks |
| CONSUMER | Product scanning, simplified compliance view |
| GUEST | Limited scanning without authentication |

### Input

- Product photographs (JPEG, PNG, WebP)
- Maximum file size: 10MB per image
- Supported resolutions: 640x480 minimum, 4000x4000 maximum
- Up to 3 images per product (front, back, side)

### Output

- Structured extracted data (MRP, quantity, manufacturer, dates, etc.)
- Product classification (category, subcategory)
- Applicable rule identification
- Per-rule compliance status (PASS / FAIL / REVIEW / NOT_APPLICABLE)
- Evidence for each rule result (OCR blocks, confidence, bounding boxes)
- Overall compliance summary
- PDF compliance report

### Core Distinction

**OCR is evidence extraction. Rule Engine is compliance decision.**

The OCR system produces structured data from images. The compliance engine makes deterministic legal decisions from that data. These are separate concerns.

### What This Project Is NOT

- This is NOT a legal certification tool
- This is NOT a replacement for physical inspection
- This does NOT verify physical quantity, weight, or measurement accuracy
- This does NOT cover FSSAI, BIS, or other regulatory frameworks (future extensibility only)
- This does NOT use LLM for legal decision-making

### Scope Boundaries

#### IN SCOPE

- Legal Metrology (Packaged Commodities) Rules, 2011 compliance
- Image-based OCR and text extraction
- Deterministic rule validation
- Evidence generation and tracking
- Role-based access control
- PDF report generation
- Local deployment only

#### OUT OF SCOPE

- FSSAI compliance
- BIS standards compliance
- Physical quantity verification
- Weight measurement validation
- Cloud deployment
- Mobile application
- LLM-based legal reasoning
- Third-party API integration
- Multi-language OCR (English + Hindi only for MVP)

### Technology Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Frontend | React + Vite | Interactive UI |
| Styling | Tailwind CSS | Rapid prototyping |
| Backend | FastAPI | Primary application server |
| ORM | SQLAlchemy 2.x | Database abstraction |
| Validation | Pydantic | API schema validation |
| Database | PostgreSQL | Relational data storage |
| Auth | JWT + Argon2 | Authentication and security |
| OCR | EasyOCR | Local text extraction |
| Image | OpenCV + Pillow | Preprocessing and CV |
| Rules | Pure Python | Deterministic validation |
| PDF | ReportLab | Report generation |
| Testing | Pytest | Backend testing |
| Migrations | Alembic | Database versioning |

### Success Criteria

1. Can analyze a product image and extract key fields (MRP, quantity, manufacturer)
2. Can map extracted data to applicable Legal Metrology rules
3. Can determine PASS/FAIL/REVIEW status for each applicable rule
4. Can generate evidence-backed compliance reports
5. Can support multiple user roles with appropriate access control
6. All tests pass
7. Every phase is documented and auditable

### Constraints

- Must run completely locally (no cloud services)
- Must not introduce Node.js or additional backend services
- Must use PostgreSQL as primary database
- Must distinguish image-verifiable checks from physical inspection requirements
- Must not claim legal certification capability
