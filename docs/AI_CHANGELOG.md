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


