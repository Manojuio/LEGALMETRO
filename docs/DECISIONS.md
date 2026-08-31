# Architectural Decisions

## Record of significant architectural decisions.

### AD-001: FastAPI as Sole Backend

**Date:** 2026-08-31

**Decision:** Use FastAPI as the only backend framework. Do NOT introduce Node.js, Express, or additional backend services.

**Rationale:**
- OCR (EasyOCR), CV (OpenCV), and rule engine are all Python
- Single language reduces complexity
- No cross-language serialization needed
- One process to deploy and maintain
- Built-in async support for concurrent operations
- Automatic OpenAPI documentation

**Consequences:**
- All backend logic in Python
- Frontend communicates with single API
- Simpler debugging and deployment

---

### AD-002: PostgreSQL as Primary Database

**Date:** 2026-08-31

**Decision:** Use PostgreSQL as the only database. No Redis, MongoDB, or other databases.

**Rationale:**
- Relational data model fits the domain
- JSON support for flexible fields (OCR results, evidence)
- SQLAlchemy 2.x provides clean ORM
- Alembic for migrations
- Locally available

**Consequences:**
- Single database to manage
- ACID compliance for data integrity
- No caching layer (acceptable for prototype)

---

### AD-003: Local File Storage

**Date:** 2026-08-31

**Decision:** Store images and reports locally in the project directory.

**Rationale:**
- No cloud storage needed
- Simple file I/O
- No external dependencies
- Easy to backup and inspect

**Consequences:**
- Limited by local disk space
- No CDN or cloud access
- File paths stored in database

---

### AD-004: JWT Authentication

**Date:** 2026-08-31

**Decision:** Use JWT tokens for stateless authentication.

**Rationale:**
- No server-side session storage
- Scalable
- Standard approach
- Easy to implement with PyJWT

**Consequences:**
- Token expiry management needed
- No server-side revocation (acceptable for prototype)
- Client must store token securely

---

### AD-005: Deterministic Rule Engine

**Date:** 2026-08-31

**Decision:** Rule engine uses only deterministic logic. No LLM for legal decisions.

**Rationale:**
- Legal compliance must be reproducible
- Deterministic results are auditable
- No hallucination risk
- Faster execution
- Testable

**Consequences:**
- Limited to rules that can be expressed programmatically
- Complex interpretation requires human review
- Review status for uncertain cases

---

### AD-006: OCR as Evidence, Not Decision

**Date:** 2026-08-31

**Decision:** OCR provides evidence (text, confidence, bounding boxes). Rule engine makes decisions.

**Rationale:**
- Separation of concerns
- OCR accuracy is independent of legal interpretation
- Evidence is auditable
- Different confidence thresholds for different purposes

**Consequences:**
- Two-stage pipeline
- OCR errors propagate as evidence quality issues
- Rule engine handles OCR uncertainty via REVIEW status

---

### AD-007: Physical Tests Out of Scope

**Date:** 2026-08-31

**Decision:** Rules requiring physical measurement (19, 20, 21) are marked as NOT_APPLICABLE or PHYSICAL_TEST_REQUIRED.

**Rationale:**
- Cannot verify physical quantity from images
- Cannot measure weight, volume physically
- Cannot perform sampling and testing
- Honest representation of system capabilities

**Consequences:**
- Some rules will always return NOT_APPLICABLE
- System explicitly does not replace physical inspection
- Documentation clearly states limitations

---

### AD-008: Single Process Architecture

**Date:** 2026-08-31

**Decision:** Run as a single FastAPI process. No background workers, no message queues.

**Rationale:**
- Local prototype
- Simple deployment
- No need for distributed processing
- Synchronous processing acceptable for single-user demo

**Consequences:**
- Long-running operations block the request
- No parallel processing (acceptable for prototype)
- Single point of failure

---

### AD-009: Role-Based Access via Dependencies

**Date:** 2026-08-31

**Decision:** Use FastAPI dependency injection for role-based access control.

**Rationale:**
- Clean separation from business logic
- Reusable dependencies
- No scattered if-else checks
- Easy to test

**Consequences:**
- Each endpoint declares required roles
- Dependencies are composable
- Access control is centralized

---

### AD-010: Evidence-Based Reporting

**Date:** 2026-08-31

**Decision:** Every rule result includes evidence (OCR blocks, bounding boxes, confidence).

**Rationale:**
- Auditability
- Defensibility
- Transparency
- Can answer "why did the system fail this rule?"

**Consequences:**
- More storage required
- More complex data model
- Richer frontend display

---

### AD-011: Single Database

**Date:** 2026-08-31

**Decision:** Use a single PostgreSQL database (`compliance_scanner`). Tests and demo/seed data share the same database.

**Rationale:**
- A separate test database adds complexity without value for a local prototype
- Seed/demo data should be visible in the same DB that the running app uses (important for SIH demo)
- Simpler connection management

**Consequences:**
- Tests can accidentally modify real data if they do not clean up after themselves
- Seed script is idempotent to avoid duplicate demo data
- One database to configure and back up

---

### AD-013: bcrypt Library Direct (not passlib)

**Date:** 2026-08-31

**Decision:** Use the `bcrypt` library directly for password hashing instead of `passlib`.

**Rationale:**
- passlib 1.7.4 is incompatible with bcrypt 4.1+ (raises `ValueError: password cannot be longer than 72 bytes` during its version-detection bug check)
- Installed bcrypt is 5.0.0
- Direct bcrypt usage is simpler and avoids the known passlib/bcrypt wrapper bug

**Consequences:**
- Password hashing handled in `app/core/security.py`
- Verified via `bcrypt.checkpw`
- No passlib dependency needed for hashing

---

### AD-014: python-jose for JWT (not PyJWT)

**Date:** 2026-08-31

**Decision:** Use `python-jose` (import `from jose import jwt`) for JWT handling, matching the already-declared `python-jose[cryptography]` dependency.

**Rationale:**
- The original plan listed "PyJWT", but the dependency installed is python-jose
- python-jose is already in pyproject.toml
- Avoids adding a redundant dependency

**Consequences:**
- Import path is `from jose import jwt`
- Phase 6 auth will use `app/core/security.py` helpers

---

### AD-012: URL-Encoded Database Password

**Date:** 2026-08-31

**Decision:** Special characters in the database password (e.g. `@`) are URL-encoded (e.g. `%40`) in the SQLAlchemy connection URL.

**Rationale:**
- `@` is the host separator in a connection URL
- Without encoding, psycopg2 fails to resolve the host name correctly

**Consequences:**
- Connection URLs must URL-encode special password characters
- The password itself is stored only in `.env` (gitignored), never in the repo
- Must remember to encode special characters in passwords

