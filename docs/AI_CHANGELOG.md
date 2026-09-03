# AI Changelog

## 2026-08-31 — Phase 1

### Task
Created project specification documentation.

### Prompt
Phase 1: Project Specification - Create documentation for the Packaged Commodities Compliance Scanner.

### Files Created
- docs/PROJECT_SCOPE.md
- docs/REQUIREMENTS.md
- docs/ROLES.md
- docs/RULE_SCOPE.md
- docs/ASSUMPTIONS.md
- docs/PHASE_STATUS.md

### Important Implementation
Documentation-only phase. Defined problem, users, scope, requirements, roles, rule scope, and assumptions.

### Why
Must freeze exactly what we're building before writing code. Rule scope must be defined before rule registry.

### Tests
N/A - Documentation phase

### Problems
None

### Decision
FastAPI as sole backend. Physical quantity verification out of scope. FSSAI/BIS out of scope.

### Human Verification
Required: Yes for legal interpretation of rule scope.

## 2026-08-31 — Phase 2

### Task
Created Legal Rule Registry with structured rule definitions.

### Prompt
Phase 2: Legal Rule Registry - Create structured JSON rules based on Legal Metrology (Packaged Commodities) Rules, 2011.

### Files Created
- rules/rules.json
- rules/categories.json
- rules/exemptions.json
- rules/standard_packages.json
- rules/README.md

### Important Implementation
17 rules extracted with automation levels. Physical test rules (19, 20) explicitly marked as not image-verifiable. Visual rules (7, 8, 9) marked as AI_ASSISTED with REVIEW fallback.

### Why
Rule registry must exist before rule engine. Rules define what the system validates.

### Tests
N/A - Registry files, not code.

### Problems
None

### Decision
Explicit separation between image-verifiable rules and physical test rules. No invented legal requirements.

### Human Verification
Required: Yes for legal accuracy of rule interpretations.

## 2026-08-31 — Phase 5

### Task
Implemented FastAPI application foundation with health/version endpoints and all SQLAlchemy models.

### Prompt
Phase 5: FastAPI Foundation — create clean FastAPI app with config, database, models, schemas, and API. Add GET /health and GET /api/v1. Configure env vars, PostgreSQL, SQLAlchemy, Pydantic settings, CORS. Add pytest tests.

### Files Created
- app/main.py
- app/core/config.py
- app/core/database.py
- app/api/system.py
- app/models/user.py
- app/models/product.py
- app/models/analysis.py
- app/models/rule.py
- app/models/inspection.py
- app/schemas/system.py
- tests/conftest.py
- tests/test_system.py
- tests/test_models.py

### Files Modified
- main.py (placeholder retained, unused)
- pyproject.toml (dependencies synced via uv)
- docs/PHASE_STATUS.md
- docs/API.md (created)
- docs/TESTING.md (created)
- docs/DATABASE.md

### Important Implementation
- Pydantic settings via `Settings` class with cached `get_settings()`
- SQLAlchemy 2.x `DeclarativeBase` with `Mapped`/`mapped_column` typing
- 12 tables matching LLD: users, products, analyses, product_images, ocr_results, extracted_fields, rules, rule_results, rule_result_evidence, inspections, reports, audit_logs
- UUID string primary keys, JSONB-style JSON columns, enum types
- CORS middleware for local React (localhost:5173, 3000)
- /health, /api/v1/health, /health/live, /health/ready, /api/v1/version endpoints

### Why
- Foundation needed before auth, OCR, or compliance code
- Single FastAPI backend per AD-001 (no Node.js)
- Ready endpoint validates DB connectivity for deployments

### Tests
pytest tests/ -v
Result: 14 passed

### Problems
- Missing `DateTime` imports in product/analysis/rule/inspection models (fixed)
- `@` in DB password broke connection URL parsing — URL-encoded as `%40` (fixed)

### Decision
- Tests use dedicated `compliance_scanner_test` database
- Readiness endpoint reports 503 when DB unreachable
- Table creation is best-effort in conftest so non-DB endpoint tests never block

### Human Verification
Required: No for code. Yes for legal interpretation in later phases.

## 2026-08-31 — Seed Data + Single Database + Security Helpers

### Task
Consolidated to a single database, added a demo-data seed script, and added reusable security helpers (needed for seeding password hashes).

### Prompt
User requested: use one database instead of two, and add test entities to the database. Also prepare for the next phase.

### Files Created
- scripts/seed_db.py
- app/core/security.py

### Files Modified
- tests/conftest.py (single DB instead of test DB)
- docs/DATABASE.md (single DB, seeding)
- docs/DECISIONS.md (AD-011 single DB, AD-013 bcrypt, AD-014 python-jose)
- docs/TESTING.md (single DB)

### Important Implementation
- Seed script creates 5 users (one per role), loads all 17 rules from rules.json, and creates 2 sample products with analyses, extracted fields, and rule results
- Seed is idempotent (re-running adds no duplicates)
- app/core/security.py provides hash_password, verify_password, create_access_token, decode_access_token

### Why
- A single DB is simpler for a local prototype; demo data should live where the app reads it
- Password hashing is required before we can seed users
- Reusable security module preps Phase 6 (auth)

### Tests
pytest tests/ -v
Result: 14 passed

### Problems
- passlib 1.7.4 incompatible with bcrypt 5.0.0 (72-byte bug) → switched to direct bcrypt (AD-013)
- Plan listed PyJWT but dependency is python-jose → used `from jose import jwt` (AD-014)
- Seed script initially used `u.role` on dicts → fixed to `u["role"]`

### Decision
Single database (AD-011). Direct bcrypt hashing (AD-013). python-jose for JWT (AD-014).

### Human Verification
Required: No.

## 2026-09-01 — Phase 9 (OCR)

### Task
Implemented the OCR pipeline: image validation, preprocessing (OpenCV/Pillow), EasyOCR recognition, and OCR endpoints.

### Prompt
User requested: "first i wan to build the core of the project that is the ocr that i will upload the image of the product and test it doc it" — build and document the OCR core first.

### Files Created
- app/services/image_service.py
- app/services/ocr_service.py
- app/schemas/image.py
- app/api/analysis.py
- scripts/generate_fixtures.py
- tests/test_ocr.py
- tests/test_analysis_api.py
- tests/fixtures/valid_tea.jpg, valid_biscuits.jpg, missing_declarations.jpg
- docs/OCR.md

### Files Modified
- app/main.py (register analysis router)
- app/core/config.py (OCR preprocessing settings)
- docs/API.md (3 new endpoints)

### Important Implementation
- `image_service.validate_image_bytes`: enforces empty/size/MIME/decode checks
- `image_service.preprocess`: decode + EXIF normalize → resize → denoise → adaptive threshold, recording each step
- `ocr_service.run_ocr`: lazy-cached EasyOCR reader → normalized blocks (text, confidence, [x,y,w,h])
- `api/analysis.py`: POST create analysis, POST upload image, POST run OCR; persists OCRResult evidence rows

### Why
OCR is the "evidence provider". It must never decide compliance. Treating it as evidence extraction keeps the Rule Engine as the sole decision maker. Building OCR first gives the team a working core to test before extraction/validation phases.

### Tests
pytest tests/ -v
Result: 31 passed

### Problems
- EasyOCR first load is slow (~120s for model load) — mitigated by caching the reader singleton; subsequent runs are fast.
- pydantic Settings can't be monkeypatched for the size-limit test — rewrote test to build an over-limit payload directly.

### Decision
- EasyOCR cached as module singleton
- Preprocessing steps recorded for auditability
- OCR accuracy measured on our own dataset only (0.82 tea fixture), not claimed generally
- Auth not yet added — analysis endpoints are public until Phase 6

### Human Verification
Required: No for code. Yes for visual/legal interpretation later.

## 2026-09-01 — Extraction + Rule Engine + Real-Image Validation

### Task
User uploaded two real product photos (`images.jpg` front, `orange-back.jpg` back of a biscuit pack) and requested: run the rules against them, test, show the output, and generate the PDF report.

### Files Created
- app/services/extraction_service.py
- app/services/classification_service.py
- app/services/compliance_service.py
- app/services/report_service.py
- app/compliance/applicability.py
- app/compliance/rule_engine.py
- app/compliance/validators/declaration.py
- app/compliance/validators/__init__.py
- app/api/analysis.py (extended: /run, /report)
- scripts/demo_scan.py
- tests/test_compliance_pipeline.py
- tests/test_extraction.py
- tests/fixtures/ (user-added images.jpg, orange-back.jpg)

### Files Modified
- app/core/config.py (OCR_MIN_CONFIDENCE=0.25)
- app/services/ocr_service.py (filter low-confidence blocks from raw_text)
- docs/API.md, docs/PHASE_STATUS.md, docs/AI_CHANGELOG.md

### Important Implementation
- Extraction is regex-based, deterministic, and never invents data (missing -> FAIL/REVIEW, never PASS)
- `run_complete_analysis()` orchestrates: images -> OCR -> extraction -> classification -> applicability -> rules -> report
- 17 rules dispatched via `run_rules`; visual rules (7/8/9) always REVIEW, physical rules (19/20) NOT_APPLICABLE from images
- Rule engine returns PASS/FAIL/REVIEW/NOT_APPLICABLE; overall = worst status
- ReportLab PDF with status color table
- Real image honesty: when OCR sees "NET WEIGHT" but not the value, Rule 12/13 return REVIEW (not FAIL); commodity label tolerant of OCR typos ("Commedity"); country matches "Product of India"; batch regex requires a digit; typed best-before date counts as a date declaration for Rule 15

### Why
Legal validation must be deterministic and evidence-driven. OCR confidence is stored as evidence; the engine never passes on unreadable data.

### Tests
pytest tests/ -v
Result: 43 passed

### Problems
- Batch regex could not capture "BN-2601" (hyphen separator) — fixed to allow `[A-Za-z]{1,4}[\d\-_/]...`
- Country regex spanned newlines ("India\nKeep In Cool") — restricted to a single line
- Commodity name picked up FSSAI category codes as residue — trimmed
- `extract_net_quantity` partial fallback exposed a None unit crash in `_load_standard_values` — guarded with REVIEW

### Decision
- OCR is evidence provider only; rule engine is the sole decision maker
- REVIEW is used whenever OCR is unreliable (net quantity value/unit, visual rules)
- Demo script supports `"file.jpg:POSITION"` multi-image scans

### Human Verification
Required: No for code. Yes for legal interpretation of rule scope.

## 2026-09-03 — OCR Engine Rebuild Phase 1 (Image Validation)

### Task
Phase 1 of the OCR engine rebuild: create a dedicated image validation
component with stable error codes and dimension checks; do not let corrupted
or invalid images reach OCR.

### Files Created
- app/services/image/__init__.py
- app/services/image/validator.py
- tests/test_image_validator.py

### Files Modified
- app/services/image_service.py (validate_image_bytes delegates to the
  validator; ImageValidationError re-exported)
- pyproject.toml (pytest testpaths)
- docs/OCR_ENGINE.md (created), docs/OCR_ENGINE_AUDIT.md,
  docs/PHASE_STATUS.md, docs/TESTING.md, docs/AI_CHANGELOG.md

### Important Implementation
- validator.py: checks in order — empty → size limit → full Pillow decode →
  format allow-list → dimension minimums; raises ImageValidationError with a
  stable code (INVALID_IMAGE, IMAGE_DECODE_FAILED, IMAGE_TOO_LARGE,
  IMAGE_TOO_SMALL, IMAGE_NOT_FOUND)
- validate_image_file(path) entry point for stored uploads (file-exists check)
- image_service.validate_image_bytes is now a thin delegation wrapper; the
  exception class is re-exported so all existing callers/tests are unchanged

### Why
- The old validator lived inside image_service.py with no error codes and no
  minimum-dimension check; tiny/corrupt images could flow to OCR
- One source of truth for validation avoids drift between modules

### AI-assisted
Yes (code written by AI, reviewed against the audit findings)

### Tests
77 passed (65 existing + 12 new), 143s; the 12 new tests cover valid/empty/
corrupt/oversized/unsupported/tiny images plus path-based validation and
image_service backward compatibility

### Result
Corrupt and undersized images are now rejected with clear, stable error
codes before they can reach OCR

### Problems
- Root-level test_images.py (dev script) was being collected by pytest and
  crashed its capture plugin on Windows — fixed by setting
  testpaths = ["tests"] in pyproject.toml

### Human Verification
Required: No.

## 2026-09-03 — OCR Engine Rebuild Phase 2 (Image Quality Assessment)

### Task
Phase 2: assess image quality (resolution, blur, brightness, contrast) with
deterministic OpenCV metrics and classify GOOD / ACCEPTABLE / POOR /
UNUSABLE without silently rejecting borderline images.

### Files Created
- app/services/image/quality.py
- tests/test_quality.py

### Files Modified
- docs/OCR_ENGINE.md, docs/PHASE_STATUS.md, docs/TESTING.md,
  docs/AI_CHANGELOG.md

### Important Implementation
- assess(image) on BGR or grayscale ndarray; assess_bytes(data) convenience
  (decodes via image_service.decode_to_cv2, which moves to preprocessing in
  Phase 3)
- Metrics: variance-of-Laplacian blur_score; mean-luminance brightness_score
  (0..1); (P98−P2)/255 contrast_score
- Grading: worst metric wins; blur bands relative to OCR_BLUR_THRESHOLD;
  brightness bands from OCR_BRIGHTNESS_LOW/HIGH with hard floors; contrast
  bands are module constants; resolution warning caps grade at POOR
- POOR stays usable (OCR may run, result must carry the warning);
  UNUSABLE (blank/no structure) sets usable=False

### Why
- The old pipeline had no quality stage at all — bad images flowed straight
  into OCR and produced low-confidence garbage without any warning
- Deterministic metrics only; no ML quality model

### AI-assisted
Yes (code written by AI, reviewed against the audit findings)

### Tests
89 passed (77 + 12 new quality tests), 169s

### Result
Every image now gets an evidence dict with grade, usable flag, metric
scores, and warnings; borderline images warn instead of being silently
rejected

### Problems
- Tiny-image test helper originally drew no content on a 60x80 canvas
  (blank → UNUSABLE instead of isolating the resolution downgrade) — fixed
  the test to draw a sharp rectangle so the POOR grade is purely
  resolution-driven

### Human Verification
Required: No.

