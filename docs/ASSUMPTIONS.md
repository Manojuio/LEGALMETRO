# Assumptions

## Technical Assumptions

### TA-01: Local Environment
- PostgreSQL is installed and running locally
- Database name: `compliance_scanner`
- Database user: `postgres`
- Database password: set via `.env` (not committed to the repository)
- Database host: `localhost`
- Database port: `5432`

### TA-02: Python Environment
- Python 3.10+ is available
- `uv` is used for Python environment management
- Virtual environment managed via `uv venv`

### TA-03: Image Quality
- Product images are reasonably clear and in focus
- Text on packaging is printed (not handwritten)
- Images are taken at reasonable angles (not extreme oblique)
- Lighting is adequate for OCR processing
- Packaging is not excessively curved or reflective

### TA-04: Language
- Primary OCR language: English
- Hindi support is optional for MVP
- Legal text analysis is English-only for prototype

### TA-05: Network
- No internet access required or used
- All processing is local
- No external API calls

## Legal Assumptions

### LA-01: Legal Source
- Legal Metrology (Packaged Commodities) Rules, 2011 is the sole legal source
- Rules are interpreted as written in the official document
- No legal interpretation beyond the rule text

### LA-02: Rule Completeness
- The rule registry covers the most impactful rules for the prototype
- Not all 26 rules may be fully implemented
- Priority is on rules verifiable from images

### LA-03: Physical Inspection
- Physical quantity verification is explicitly out of scope
- Sampling and testing requirements are noted but not implemented
- The system does not replace physical inspection

### LA-04: Regulatory Scope
- FSSAI compliance is out of scope
- BIS standards compliance is out of scope
- Only Legal Metrology rules are implemented
- Future extensibility is documented but not built

## Business Assumptions

### BA-01: Users
- Users understand the system provides compliance guidance, not certification
- Users are responsible for verifying results before taking action
- The system is a prototype, not a production compliance tool

### BA-02: Product Data
- Product categories are predefined in the system
- Standard package quantities are predefined
- Category-specific rules are configured in the rule registry

### BA-03: Evidence
- Evidence is based on OCR output and image analysis
- Evidence may be incomplete if OCR fails on parts of the label
- Confidence scores are estimates, not guarantees

## Architecture Assumptions

### AA-01: FastAPI Only
- FastAPI is the sole backend framework
- No Node.js, Express, or additional backend services
- All business logic runs in the FastAPI application

### AA-02: Monolithic Architecture
- Single application server
- No microservices
- No message queues
- No background task processing (for prototype)

### AA-03: File Storage
- Images stored locally in `uploads/` directory
- Reports stored locally in `reports/` directory
- No cloud storage

### AA-04: Database
- PostgreSQL is the only database
- No Redis, MongoDB, or other databases
- SQLAlchemy manages all database operations

## Testing Assumptions

### TA-01: Test Coverage
- Every endpoint has at least one test
- Every service has unit tests
- Test dataset includes valid and invalid cases
- Test results are documented

### TA-02: Test Data
- Test images are provided manually
- Test data includes edge cases
- Expected results are documented

## Limitations Acknowledged

### LA-01: OCR Accuracy
- OCR accuracy varies by image quality
- No claimed accuracy percentage until measured
- Low-confidence results are flagged for review

### LA-02: Rule Completeness
- Not all legal rules are implemented
- Some rules require physical measurement
- Some rules require human judgment

### LA-03: Prototype Status
- This is a prototype for SIH evaluation
- Not production-ready
- Not a legal compliance tool
- Not a certification system

## Unresolved Questions

1. Should GUEST scanning persist results to database?
2. How many test images are needed per product category?
3. Should the system support batch analysis (multiple products)?
4. What is the maximum number of images per analysis?
5. Should reports include QR codes for verification?
