# Requirements

## Functional Requirements

### FR-01: Image Upload

- User can upload 1-3 product images per analysis
- Supported formats: JPEG, PNG, WebP
- Maximum size: 10MB per image
- Minimum resolution: 640x480
- Maximum resolution: 4000x4000
- System validates image integrity before processing
- System rejects corrupt or unsupported files

### FR-02: OCR Processing

- System preprocesses images (resize, denoise, contrast enhancement)
- EasyOCR extracts text with confidence scores and bounding boxes
- OCR output is normalized into text blocks
- Low-confidence blocks are flagged for review
- OCR is treated as evidence extraction, not compliance decision

### FR-03: Information Extraction

- System extracts structured fields from OCR output:
  - MRP (Maximum Retail Price)
  - Net Quantity
  - Unit of measurement
  - Manufacturer name
  - Manufacturer address
  - Consumer care contact
  - Date of manufacturing/packing
  - Best before/use by date
  - Generic/product name
  - Commodity description
- Extraction uses regex, keyword matching, and pattern recognition
- Each extracted field includes confidence score

### FR-04: Product Classification

- System classifies product into category and subcategory
- Initial categories: FOOD, BEVERAGE, COSMETIC, PHARMACEUTICAL, ELECTRONICS, GENERAL
- Classification based on extracted text keywords and product name
- Classification includes confidence score

### FR-05: Applicability Determination

- System determines which Legal Metrology rules apply to the product
- Applicability based on:
  - Product category
  - Package type
  - Package size
  - Sale type (retail, wholesale, export)
- Returns list of applicable rule numbers

### FR-06: Compliance Validation

- Each applicable rule is validated deterministically
- Validation produces four states:
  - PASS: Requirement satisfied
  - FAIL: Requirement not satisfied
  - REVIEW: Cannot determine from image alone
  - NOT_APPLICABLE: Rule does not apply after deeper inspection
- Each result includes reason, evidence, and confidence

### FR-07: Visual/CV Checks

- Font size estimation (Rule 7)
- Text placement and spacing (Rule 8)
- Legibility and contrast assessment (Rule 9)
- Visual checks return REVIEW where measurement is unreliable
- No fake physical millimetre measurements

### FR-08: Evidence System

- Every rule result includes evidence:
  - Related OCR text blocks
  - Bounding boxes
  - Confidence scores
  - Validator used
  - Timestamp
- Evidence is stored in database and displayed in UI
- Evidence is auditable

### FR-09: Compliance Reports

- PDF report includes:
  - Product information
  - Analysis metadata
  - Applicable rules summary
  - Per-rule results with evidence
  - Overall compliance status
  - Limitations and disclaimers
  - Generation timestamp

### FR-10: Role-Based Access Control

- Five roles: ADMIN, LMO, MANUFACTURER, RETAILER, CONSUMER
- Access control on endpoints, not on compliance engine
- JWT-based authentication
- Role-based dependencies, not scattered if-else checks

### FR-11: Product Management

- Manufacturers can create and manage products
- Products store basic metadata (name, category, brand)
- Products link to analyses and images

### FR-12: Inspection Workflow (LMO)

- LMO can create inspection records
- Inspections link to products, analyses, and observations
- Inspection status tracking (PENDING, IN_PROGRESS, COMPLETED)
- Physical inspection findings recorded separately from image analysis

## Non-Functional Requirements

### NFR-01: Local Deployment

- Application runs entirely on local machine
- No external API calls
- No cloud services
- PostgreSQL runs locally

### NFR-02: Deterministic Rule Engine

- Rule validation produces consistent results for same inputs
- No randomness or LLM involvement in legal decisions
- Rules are testable and auditable

### NFR-03: Testability

- Every endpoint has pytest tests
- Every service has unit tests
- Every model has relevant tests
- Test dataset of 70+ cases
- Test results documented

### NFR-04: Documentation

- Every phase documented in docs/
- Every code change logged in AI_CHANGELOG.md
- Architecture decisions recorded in DECISIONS.md
- API documentation for every endpoint
- Known limitations documented

### NFR-05: Maintainability

- Modular code structure
- Clear separation of concerns
- Services separated from API routes
- Validators separated from rule definitions
- Configuration externalized

## Acceptance Criteria

| ID | Criterion | Verification |
|----|-----------|-------------|
| AC-01 | Image upload accepts valid JPEG/PNG/WebP | Automated test |
| AC-02 | OCR extracts text with confidence scores | Automated test |
| AC-03 | Extraction produces structured fields | Automated test |
| AC-04 | Rule engine applies correct rules per category | Automated test |
| AC-05 | Compliance results are deterministic | Automated test |
| AC-06 | Evidence is stored and retrievable | Automated test |
| AC-07 | PDF report is generated correctly | Automated test |
| AC-08 | Authentication works with JWT | Automated test |
| AC-09 | Role-based access is enforced | Automated test |
| AC-10 | Physical quantity claims are NOT made | Manual review |
| AC-11 | LLM is NOT used for legal decisions | Code review |
| AC-12 | All tests pass | Test run |
