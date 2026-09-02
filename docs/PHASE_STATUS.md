# Phase Status

## Phase 1: Project Specification
- **Status:** COMPLETED
- **Date:** 2026-08-31
- **Files Created:**
  - docs/PROJECT_SCOPE.md
  - docs/REQUIREMENTS.md
  - docs/ROLES.md
  - docs/RULE_SCOPE.md
  - docs/ASSUMPTIONS.md
- **Decisions:**
  - FastAPI is sole backend (no Node.js)
  - PostgreSQL with password stored in `.env` (not committed)
  - uv for Python environment
  - Legal Metrology Rules 2011 is sole legal source
  - Physical quantity verification is OUT OF SCOPE
  - FSSAI/BIS are OUT OF SCOPE
- **Assumptions:**
  - Local PostgreSQL available
  - Images are reasonably clear
  - English text primary
- **Next Phase:** Phase 2 - Legal Rule Registry

## Phase 2: Legal Rule Registry
- **Status:** COMPLETED
- **Date:** 2026-08-31
- **Files Created:**
  - rules/rules.json (17 rules)
  - rules/categories.json (6 categories, 17 subcategories)
  - rules/exemptions.json (7 exemptions)
  - rules/standard_packages.json (4 unit types + category-specific)
  - rules/README.md
- **Decisions:**
  - 17 rules extracted covering declarations, quantity, price, manufacturer, dates, visual, physical, administrative
  - Physical test rules (19, 20) marked as PHYSICAL_TEST_REQUIRED
  - Visual rules (7, 8, 9) marked as AI_ASSISTED
  - All other image-verifiable rules marked as AUTOMATED
  - Exemptions defined for export, institutional, small packages, non-retail, gift, pharmaceutical, agricultural
- **Next Phase:** Phase 3 - HLD

## Phase 3: HLD
- **Status:** COMPLETED
- **Date:** 2026-08-31
- **Files Created:**
  - docs/ARCHITECTURE.md
  - docs/DATA_FLOW.md
  - docs/DECISIONS.md
- **Decisions:**
  - FastAPI as sole backend (no Node.js) — documented rationale
  - Single process architecture for local prototype
  - RBAC via FastAPI dependencies (centralized)
  - OCR as evidence provider, rule engine as decision maker
  - Physical tests out of scope
  - Evidence-based reporting for auditability
- **Next Phase:** Phase 4 - LLD + Database

## Phase 4: LLD + Database
- **Status:** COMPLETED
- **Date:** 2026-08-31
- **Files Created:**
  - docs/LLD.md (11 tables, indexes, enums, relationships)
  - docs/DATABASE.md (connection, setup, migration commands)
- **Decisions:**
  - UUID primary keys for all tables
  - JSONB for flexible fields (OCR results, evidence)
  - Separate rule_result_evidence table for auditability
  - Enums for status fields
  - Analysis owns the central relationship chain
- **Next Phase:** Phase 5 - FastAPI Foundation

## Phase 5: FastAPI Foundation
- **Status:** COMPLETED
- **Date:** 2026-08-31
- **Files Created:**
  - app/main.py
  - app/core/config.py
  - app/core/database.py
  - app/api/system.py
  - app/models/*.py (12 tables)
  - app/schemas/system.py
  - tests/conftest.py
  - tests/test_system.py
  - tests/test_models.py
  - docs/API.md
  - docs/TESTING.md
- **Endpoints Added:**
  - GET /health
  - GET /api/v1
  - GET /api/v1/health
  - GET /api/v1/health/live
  - GET /api/v1/health/ready
  - GET /api/v1/version
- **Database:**
  - Single database `compliance_scanner` (no separate test DB)
  - All 12 tables created in PostgreSQL via SQLAlchemy metadata
  - Configured connection (`@` in password URL-encoded as `%40`)
  - Seeded demo data via `python -m scripts.seed_db` (5 users, 17 rules, 2 products, 2 analyses)
- **Tests:** 14 passed
- **Files Created:**
  - scripts/seed_db.py
  - app/core/security.py
- **Decisions:**
  - Single database (AD-011)
  - bcrypt direct instead of passlib (AD-013)
  - python-jose for JWT (AD-014)
- **Next Phase:** Phase 6 - Authentication + RBAC

## Phase 6: Authentication + RBAC
- **Status:** COMPLETED
- **Date:** 2026-09-02
- **Files Created:**
  - app/schemas/auth.py (RegisterRequest, LoginRequest, UserOut, TokenResponse, UserUpdateRequest, ZoneOut)
  - app/core/deps.py (get_current_user, require_roles, get_current_lmo)
  - app/api/auth.py (register, login, me, zones CRUD, user list/update, admins/lmos)
  - app/models/user.py (Zone model + users.zone_id)
  - app/core/security.py (reused: bcrypt + python-jose)
- **Endpoints Added:**
  - POST /api/v1/auth/register, POST /api/v1/auth/login, GET /api/v1/auth/me
  - POST/GET /api/v1/zones (ADMIN), GET /api/v1/users (ADMIN)
  - PATCH /api/v1/users/{id} (ADMIN, zone assignment), GET /api/v1/admins/lmos (ADMIN)
- **Database Change:** new `zones` table + `users.zone_id` column (added via ALTER TABLE on existing DB)
- **Decisions:** Self-registration restricted to CONSUMER/RETAILER/MANUFACTURER; ADMIN/LMO elevated roles require admin; analysis/product/inspection endpoints now JWT-protected with ownership checks.

## Phase 7: Product Management
- **Status:** COMPLETED
- **Date:** 2026-09-02
- **Files Created:** app/api/products.py
- **Endpoints Added:**
  - GET /api/v1/products (ADMIN/LMO/MANUFACTURER/RETAILER)
  - POST/PATCH/DELETE /api/v1/products (ADMIN, or owning MANUFACTURER)
- **Decisions:** CONSUMER cannot view products; MANUFACTURER can only modify own products (created_by check).

## Phase 8: Image Upload
- **Status:** COMPLETED (with Phase 9)
- **Date:** 2026-09-01
- **Files:**
  - app/services/image_service.py (validation: empty/size/MIME/decode; preprocessing: resize/denoise/threshold)
  - POST /api/v1/analyses/{id}/images endpoint
- **Decisions:** Image binaries on disk, metadata in DB; EXIF transpose before OCR; preprocessing steps recorded for audit.

## Phase 9: OCR
- **Status:** COMPLETED
- **Date:** 2026-09-01
- **Files Created:**
  - app/services/image_service.py
  - app/services/ocr_service.py
  - app/schemas/image.py
  - app/api/analysis.py
  - scripts/generate_fixtures.py
  - tests/fixtures/*.jpg
  - tests/test_ocr.py
  - tests/test_analysis_api.py
  - docs/OCR.md
- **Endpoints Added:**
  - POST /api/v1/analyses
  - POST /api/v1/analyses/{id}/images
  - POST /api/v1/analyses/{id}/ocr
- **Database:**
  - Uses existing `product_images`, `ocr_results`, `analyses` tables
  - No schema change needed (tables already existed from Phase 4/5)
- **Tests:** 31 passed (7 new OCR tests + 7 analysis API tests)
- **Decisions:**
  - OCR is evidence extraction only, not compliance decision (central principle)
  - EasyOCR reader cached as module-level singleton to avoid reload per request
  - Image binaries stored on disk, only metadata in DB
  - Preprocessing steps recorded in `steps_applied` for auditability
  - Accuracy measured on own test dataset only (0.82 on tea fixture), not claimed generally
  - Low-confidence OCR blocks (conf < OCR_MIN_CONFIDENCE=0.25) excluded from extraction text but kept as evidence
- **Known Limitations:**
  - Photos at angle / curved packaging reduce accuracy
  - Font size not measured precisely (visual rules enforce REVIEW)
  - Physical quantity never verified from image
- **Next Phase:** Phase 10 - Information Extraction

## Phase 10: Information Extraction
- **Status:** COMPLETED (working core)
- **Date:** 2026-09-01
- **Files Created:**
  - app/services/extraction_service.py
  - tests/test_extraction.py
- **Fields Extracted:** commodity_name (OCR-typo tolerant), generic_name, manufacturer_name, manufacturer_address, country_of_origin (Made in / Product of India), net_quantity (value/unit/numeric, partial REVIEW fallback), mrp, batch_number (requires digit; handles BN-2601 style), packing_date, best_before_date (duration form accepted), expiry_date, consumer_care_contact, dates
- **Principles:**
  - Extraction never invents data; missing field => not present (engine decides FAIL/REVIEW)
  - REgex-based, deterministic, auditable source_text on every field
  - Net-quantity label seen but unit unreadable => partial field (REVIEW), never FAIL
- **Next Phase:** Phase 11

## Phase 11: Product Classification
- **Status:** COMPLETED (keyword-based working core)
- **Date:** 2026-09-01
- **Files Created:** app/services/classification_service.py
- **Decisions:** Keyword matching on extracted text against rules/categories.json; supports multi-image evidence.

## Phase 12: Applicability Engine
- **Status:** COMPLETED (working core, exemptions applied + build-level included)
- **Date:** 2026-09-01
- **Files Created:** app/compliance/applicability.py + rules/exemptions.json usage
- **Decisions:** Physical test rules (19/20) NOT_APPLICABLE from image-only evidence; visual rules (7/8/9) AI_ASSISTED => REVIEW.

## Phase 13: Compliance Engine
- **Status:** COMPLETED (working core)
- **Date:** 2026-09-01
- **Files Created:**
  - app/compliance/rule_engine.py (run_rules, aggregate_overall)
  - app/compliance/validators/declaration.py (Status, ValidationOutcome)
- **Decisions:**
  - Overall status = worst of individual rule statuses (PASS < REVIEW < FAIL)
  - Validators can return REVIEW for unreliable-but-present evidence (net quantity, visual rules)
  - Rules 3/4/6/etc. aggregate RequiredDeclarations across extracted fields and evidence
- **Tests:** 43 passed total (incl. test_extraction.py 8, test_compliance_pipeline.py 4)
- **Full suite now:** 61 passed (after Phase 6/7/18 + JWT auth updates to analysis/pipeline tests)

## Phase 14: CV Checks
- **Status:** DEFERRED (font-size/measurement checks stay REVIEW; rules 7/8/9 honest)

## Phase 15: Complete /analyze endpoint
- **Status:** COMPLETED (working core)
- **Date:** 2026-09-01
- **Files Created:** app/services/compliance_service.py (run_complete_analysis orchestration) + POST /api/v1/analyses/{id}/run

## Phase 16: Evidence System
- **Status:** COMPLETED (working core)
- **Date:** 2026-09-01
- **Files Created:** evidence persisted per check (type, field, value, confidence, partial flags); ocr_results rows keep low-confidence blocks.

## Phase 17: Reports
- **Status:** COMPLETED (working core)
- **Date:** 2026-09-01
- **Files Created:** app/services/report_service.py (ReportLab) + GET /api/v1/analyses/{id}/report
- **Output:** PDF with product summary, per-rule color-coded status table (PASS/REVIEW/FAIL), evidence, and limitations disclaimer.
- **Test:** test_report_generation_after_run asserts `%PDF` header;
  verified real report on biscuit images (demo_analysis_*.pdf under reports/).

## Phase 18: Inspection Workflow
- **Status:** COMPLETED
- **Date:** 2026-09-02
- **Files Created:** app/api/inspections.py
- **Endpoints Added:**
  - POST/GET /api/v1/inspections (ADMIN / LMO)
  - PATCH/GET /api/v1/inspections/{id} (ADMIN / owning LMO)
  - GET /api/v1/dashboard/summary (all roles, role-aware; ADMIN sees lmos_by_zone)
- **Decisions:** LMO sees only own inspections; ADMIN sees all; inspection attaches to an existing analysis.

## Phase 19: React Frontend
- **Status:** COMPLETED
- **Date:** 2026-09-02
- **Files Created:** frontend/ (Vite + React 18 + React Router)
  - src/auth/AuthContext.jsx, src/api.js, src/components/Layout.jsx
  - src/pages/{Login,Register,Dashboard,Analyze,AnalysisDetail,Admin}.jsx, src/styles.css
- **Flow:** Login/register → role-based dashboard → image-upload analysis (create → upload → run → PDF report) → field inspection (ADMIN/LMO).
- **Dashboards:** ADMIN sees LMOs by zone + zone assignment; LMO sees own inspections; MANUFACTURER sees products + own analyses; RETAILER/CONSUMER own analyses.
- **Decisions:** Vite dev server (port 5173) proxies /api to backend (8000); CORS allows localhost:5173; PDF report downloaded via authenticated fetch (not plain link).

## Phase 20: Interactive Analysis UI
- **Status:** PENDING
