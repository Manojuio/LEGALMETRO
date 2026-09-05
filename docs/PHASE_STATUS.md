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

---

# OCR Engine Rebuild (image → OCR → field extraction)

Rebuild of the core OCR/vision pipeline per the engine spec. Tracked with its
own phase list; full design in docs/OCR_ENGINE.md and the Phase 0 audit in
docs/OCR_ENGINE_AUDIT.md. One phase at a time, STOP for review after each.

## Rebuild Phase 0: Audit
- **Status:** COMPLETED
- **Date:** 2026-09-03
- **Files Created/Updated:** docs/OCR_ENGINE_AUDIT.md (re-verified against code)
- **Findings:** 6-variant/3-pass OCR unproven; config toggles dead; no quality
  assessment; no line reconstruction; no field status/conflict/traceability;
  duplicated OCR loops; dead code; per-image failure tolerance missing.

## Rebuild Phase 1: Image Validation
- **Status:** COMPLETED
- **Date:** 2026-09-03
- **Files Created:**
  - app/services/image/__init__.py
  - app/services/image/validator.py (validate_image_bytes, validate_image_file,
    ImageValidationError with stable codes, INVALID_IMAGE / IMAGE_DECODE_FAILED /
    IMAGE_TOO_LARGE / IMAGE_TOO_SMALL / IMAGE_NOT_FOUND)
  - tests/test_image_validator.py (12 tests)
- **Files Modified:**
  - app/services/image_service.py (validate_image_bytes delegates to validator;
    ImageValidationError re-exported — existing callers unchanged)
  - pyproject.toml (testpaths = ["tests"] — root test_images.py dev script was
    crashing pytest's capture plugin on Windows)
- **API Changes:** none (endpoints and response shapes unchanged)
- **Database Changes:** none
- **Tests:** 77 passed (65 existing + 12 new), 143s
- **Decisions:** size check before decode; format check on decoded container;
  legacy single-arg ImageValidationError kept for compatibility
- **Limitations:** multi-frame/EXIF beyond first frame handled in later phases
- **Next Phase:** Rebuild Phase 2 - Image Quality Assessment

## Rebuild Phase 2: Image Quality Assessment
- **Status:** COMPLETED
- **Date:** 2026-09-03
- **Files Created:**
  - app/services/image/quality.py (assess / assess_bytes / ImageQuality;
    deterministic blur/brightness/contrast metrics; GOOD/ACCEPTABLE/POOR/
    UNUSABLE grading; warnings)
  - tests/test_quality.py (12 tests)
- **API Changes:** none
- **Database Changes:** none
- **Tests:** 89 passed (77 + 12 new), 169s
- **Decisions:** worst-metric-wins grading; POOR stays usable (OCR runs with a
  warning); UNUSABLE == blank/no structure, usable=False; blur threshold from
  OCR_BLUR_THRESHOLD, brightness bands from OCR_BRIGHTNESS_LOW/HIGH; contrast
  bands are module constants pending Phase 15 calibration; original image never
  modified
- **Limitations:** global (not per-region) blur; no angle/perspective measure;
  contrast bands uncalibrated against real photos until Phase 15
- **Next Phase:** Rebuild Phase 3 - Baseline Preprocessing

## Rebuild Phase 3: Baseline Preprocessing
- **Status:** COMPLETED (module + tests; not yet wired into live pipeline)
- **Date:** 2026-09-03
- **Files Created / Existing:**
  - app/services/image/preprocessing.py (existing, Phase 3 baseline: decode →
    resize → grayscale → denoise → CLAHE → deskew/threshold; original never
    modified; bbox_to_original coordinate mapping)
  - tests/test_preprocessing.py (16 tests, existing)
- **Wiring:** the module is complete and tested. It is now wired in via the
  Phase 13 orchestrator (app/services/analysis/ocr_pipeline.py) and supersedes
  the old ``image_service.preprocess()`` 6-variant system (audit finding P16).
- **Tests:** engine-level (image/) verified within full suite.
- **Next Phase:** Rebuild Phase 4 - EasyOCR engine

## Rebuild Phase 4: EasyOCR Engine
- **Status:** COMPLETED (single-pass engine; not yet wired into live pipeline)
- **Date:** 2026-09-03
- **Files Created:**
  - app/services/ocr/__init__.py
  - app/services/ocr/engine.py (run_ocr single pass, lazy singleton reader,
    image_id-aware evidence blocks, raw/normalized text, OCR_NO_TEXT / OCR_FAILED)
  - tests/test_ocr_engine.py (10 tests)
- **Decisions:**
  - Single EasyOCR pass over one preprocessed grayscale image — removes the
    old 6-variant / 3-pass fusion (audit P1, P16) until a golden dataset
    proves an extra operation helps (Phase 15).
  - Blocks are evidence-first: carry image_id, raw_text, normalized_text,
    confidence, bbox, engine. Full traceability.
  - Blank/empty OCR output → OCRNoTextError(OCR_NO_TEXT); corrupt/empty input
    → OCREngineError(OCR_FAILED). Callers handle per-image isolation (Phase 13).
  - Reader stays a module-level lazy singleton (moved from ocr_service.py).
- **Wire-in:** wired into the live ``/run`` and ``/ocr`` paths via the Phase 13
  orchestrator (ocr_pipeline.py), which calls ``ocr/engine.run_ocr`` instead of
  ``ocr_service.run_ocr``. The legacy ``ocr_service`` remains for backward
  compatibility but is superseded by the engine path.
- **Tests:** 116 passed (106 baseline + 10 new engine tests), ~2m
- **Next Phase:** Rebuild Phase 5 - OCR normalization

## Rebuild Phase 5: OCR Normalization
- **Status:** COMPLETED
- **Date:** 2026-09-03
- **Files Created:**
  - app/services/ocr/normalizer.py (NormalizedBlock, normalize(), normalize_blocks())
  - covered by tests/test_ocr_engine_phases.py (whitespace collapse, noise stripping)
- **Decisions:** raw_text kept verbatim; normalized_text non-destructive; never fabricates
- **Next Phase:** Rebuild Phase 6 - Text line reconstruction

## Rebuild Phase 6: Text Line Reconstruction
- **Status:** COMPLETED
- **Date:** 2026-09-03
- **Files Created:** app/services/ocr/line_builder.py (TextLine, build_lines, join_lines, sort_lines_by_top)
- **Decisions:** vertical-center band grouping + left-to-right ordering; keeps block provenance in each line
- **Next Phase:** Rebuild Phase 7 - Deterministic field extraction

## Rebuild Phase 7: Deterministic Field Extraction
- **Status:** COMPLETED
- **Date:** 2026-09-03
- **Files Created:** app/services/extraction/fields.py (extract_fields over reconstructed lines, evidence-aware)
- **Decisions:** regexes ported from extraction_service.py (with re.MULTILINE for manufacturer/address per legacy);
  every field carries image_id/bbox/status; net-quantity label-without-value → UNCERTAIN
- **Next Phase:** Rebuild Phase 8 - Field normalization

## Rebuild Phase 8: Field Normalization
- **Status:** COMPLETED
- **Date:** 2026-09-03
- **Files Created:** app/services/extraction/normalizer.py (canonical_unit, normalize_quantity, parse_number, strip_currency, is_price_context, normalize_due_date)
- **Decisions:** kg→g (×1000), l→ml (×1000); unknown units never scaled (no invented data)

## Rebuild Phase 9: Evidence + Confidence
- **Status:** COMPLETED
- **Date:** 2026-09-03
- **Files Created:**
  - app/services/extraction/evidence.py (FieldStatus enum, FieldEvidence, FieldCollection)
  - app/services/extraction/confidence.py (combine = ocr_confidence × extraction_confidence; field_status)
- **Decisions:** field confidence = OCR conf × extractor conf (cap 0.95); DETECTED/UNCERTAIN/MISSING/CONFLICTING

## Rebuild Phases 10 & 11: Multi-Image Merge + Conflict Detection
- **Status:** COMPLETED
- **Date:** 2026-09-03
- **Files Created:** app/services/analysis/evidence_merger.py (merge_collections, resolve_conflicts)
- **Decisions:** per-image collections merged per field; scalar fields with differing normalized values → CONFLICTING; UNCERTAIN ev/sec preserved

## Rebuild Phase 12: Debug Visualization
- **Status:** COMPLETED
- **Date:** 2026-09-03
- **Files Created:** app/services/ocr/visualization.py (draw_ocr_boxes)
- **Decisions:** writes PNG under OCR_DEBUG_DIR only when OCR_ENABLE_DEBUG=True; never affects evidence

## Rebuild Phase 13: End-to-End Orchestrator + Wiring
- **Status:** COMPLETED
- **Date:** 2026-09-03
- **Files Created:**
  - app/services/analysis/ocr_pipeline.py (run_pipeline orchestrator)
- **Files Modified:** app/services/compliance_service.py (uses new pipeline), app/api/analysis.py (/ocr uses orchestrator — duplicate loop removed)
- **Decisions:** validate → quality → preprocess → single-pass OCR → normalize → line build → extract → merge/conflict;
  per-image failure isolation (one bad image never aborts); persists OCRResult + source-image-aware ExtractedField rows
- **Tests:** 146 passed (was 116; +26 phase unit tests + 4 pipeline/e2e + golden)

## Rebuild Phase 14: Performance Measurement
- **Status:** COMPLETED
- **Date:** 2026-09-03
- **Files Created:** per-stage timings in ocr_pipeline.PipelineOutput.timings (processing/ocr/line/extraction/total per image)
- **Decisions:** stage timing recorded per image; reader is a module singleton (loaded once)

## Rebuild Phase 15: Golden Dataset Evaluation
- **Status:** COMPLETED
- **Date:** 2026-09-03
- **Files Created:**
  - tests/fixtures/ocr/expected/fields.json (ground-truth expected fields for tea/salt/biscuits fixtures)
  - scripts/evaluate_golden.py (evaluation harness: per-fixture, per-field accuracy)
  - tests/test_extraction_evidence.py::test_golden_dataset_extraction_accuracy
- **Results:** deterministic extraction layer = **100%** accuracy on the golden dataset (honest ground truth;
  OCR itself remains measured separately on real photos and is non-deterministic)
- **Next Phase:** none — engine rebuild COMPLETE
