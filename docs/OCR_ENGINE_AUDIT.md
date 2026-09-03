# OCR Engine Audit — Phase 0

**Date:** 2026-09-03 (verified against current codebase)
**Scope:** Full audit of the existing image → OCR → field-extraction engine
**Status:** COMPLETE

---

## 1. Current OCR Architecture

### Current Pipeline (as implemented)

```
Upload (POST /analyses/{id}/images)
  → validate_image_bytes()          [image_service.py]  empty/size/MIME/decode
  → save_upload()                   [image_service.py]  bytes → uploads/analysis_<id>/

Run (POST /analyses/{id}/ocr  OR  POST /analyses/{id}/run)
  → preprocess(data)                [image_service.py]  ← OLD pipeline, still called
      → decode_to_cv2()             Pillow decode + EXIF transpose → BGR
      → resize (max OCR_MAX_IMAGE_DIM=1800)
      → grayscale
      → bilateralFilter (only if variance > 2000)
      → _build_variants()           up to 6 image variants (gray, clahe,
                                    upscaled, otsu, deskew, invert)
  → run_ocr(preprocessed)           [ocr_service.py]
      → _pick_variants()            top 3 variants (baseline gray first)
      → _run_pass() × 3             EasyOCR over each selected variant
      → _merge_results()            coordinate rescale → cluster → de-dup
  → run_extraction(raw_text)        [extraction_service.py] regex field extraction
  → classify()                      [classification_service.py] keyword category
  → applicability → rule_engine     [compliance_service.py + app/compliance/]
```

### Dual Preprocessing Systems

A critical finding: there are **two separate preprocessing modules** and the new one is NOT wired in:

| Module | Status | Called by pipeline? |
|--------|--------|-------------------|
| `app/services/image_service.py` | OLD, variant-based, still active | YES — called by `api/analysis.py` and `compliance_service.py` |
| `app/services/image/preprocessing.py` | NEW, clean baseline, Phase 3 | NO — not imported by any pipeline code |

The new `image/preprocessing.py` exists with full decode, resize, grayscale, denoise, CLAHE, deskew, threshold, coordinate mapping, and a `PreprocessedImage` dataclass — but the pipeline still calls `image_service.preprocess()` which uses the old variant system.

### File Inventory

| File | Lines | Status |
|------|-------|--------|
| `app/services/image_service.py` | 293 | **REPLACE** — old pipeline, mixed concerns, 6-variant system |
| `app/services/ocr_service.py` | 260 | **REPLACE** — multi-variant fusion, no line reconstruction, no image_id |
| `app/services/extraction_service.py` | 431 | **PARTIAL REUSE** — regexes good, structure needs rebuild |
| `app/services/compliance_service.py` | 183 | **ADAPT** — orchestration, call new pipeline |
| `app/services/classification_service.py` | 80 | **PRESERVE** — independent, out of scope |
| `app/services/image/validator.py` | 135 | **PRESERVE** — Phase 1, complete, tested |
| `app/services/image/quality.py` | 208 | **PRESERVE** — Phase 2, complete, tested |
| `app/services/image/preprocessing.py` | 324 | **PRESERVE** — Phase 3, exists but not wired in |
| `app/services/image/__init__.py` | 5 | **UPDATE** — add preprocessing mention |
| `app/core/config.py` | 90 | **PRESERVE** — all OCR toggles already defined |
| `app/models/analysis.py` | 177 | **EXTEND** — add optional evidence columns |
| `app/schemas/image.py` | 49 | **REBUILD** — OCRResponse doesn't match actual output |
| `app/api/analysis.py` | 405 | **ADAPT** — replace duplicated OCR loops |
| `app/compliance/scoring.py` | 165 | **PRESERVE** — out of scope |
| `tests/test_ocr.py` | 122 | **EXPAND** — structure-only, no quality/line tests |
| `tests/test_extraction.py` | 102 | **EXPAND** — good coverage, no status/conflict tests |
| `tests/test_image_validator.py` | 147 | **PRESERVE** — Phase 1 tests, complete |
| `tests/test_quality.py` | 151 | **PRESERVE** — Phase 2 tests, complete |
| `tests/test_preprocessing.py` | 253 | **PRESERVE** — Phase 3 tests, exist but against new module |
| `tests/test_compliance_pipeline.py` | 79 | **PRESERVE** — integration test |
| `scripts/generate_fixtures.py` | 107 | **PRESERVE** |

### Directories Scaffolded

```
app/services/analysis/      (empty — for ocr_pipeline.py, evidence_merger.py, confidence.py)
app/services/extraction/    (empty — for fields.py, normalizer.py, evidence.py)
app/services/image/         (has validator.py, quality.py, preprocessing.py)
app/services/ocr/           (has engine.py — Phase 4)
```

---

## 2. Existing OpenCV Architecture

### What `image_service.py` does (OLD — to be replaced)

**Validation** (lines 54–61): delegates to `image/validator.py`. Sound.

**Decoding** (lines 64–77): Pillow → `ImageOps.exif_transpose` → RGB → BGR. Correct.

**Preprocessing** (lines 249–293):
- Resize to max dimension (1800), aspect preserved
- Grayscale
- Conditional bilateral denoise only when pixel variance > 2000
- Delegates to `_build_variants()`

**Variant system** (lines 186–246): builds **up to 6 variants** per image —
grayscale baseline, CLAHE, 2×/1.5× upscale, Otsu binarized, deskewed (if
Hough finds 0.4°–35°), inverted (if mean luminance < 90) — then byte-dedups.

### What `image/preprocessing.py` does (NEW — Phase 3, not wired in)

- Decode via Pillow + EXIF transpose → BGR
- Resize within configured max dimension (downscale only)
- Grayscale
- Light denoise (bilateral, only when variance > threshold)
- CLAHE contrast enhancement (config-gated or auto-triggered on low contrast)
- Deskew (config-gated via OCR_ENABLE_DESKEW)
- Threshold (config-gated via OCR_ENABLE_THRESHOLD)
- Original image NEVER modified (`.original` preserved)
- Coordinate mapping: `.bbox_to_original()` maps OCR coords back to original
- Options configurable: max_dim, denoise, clahe, deskew, threshold

### Verified Problems with OLD system

1. **6-variant/3-pass OCR** with no measured evidence that fusion beats a single pass. Biggest reliability/performance risk.
2. **Config toggles are dead code.** `OCR_ENABLE_DESKEW`, `OCR_ENABLE_CLAHE`, `OCR_ENABLE_THRESHOLD` exist in config.py but are never read by the old pipeline. Only `OCR_DENOISE` is honoured.
3. **No image quality assessment in pipeline.** blur/brightness/contrast thresholds defined in config but never used by old image_service.py.
4. **No minimum-dimension validation in pipeline.** `OCR_MIN_IMAGE_WIDTH/HEIGHT` exist but old pipeline doesn't check them.
5. **Mixed concerns** in image_service.py: validation, decoding, storage, preprocessing, variant building all in one module.
6. **Denoise gate is arbitrary** — variance > 2000 → bilateral. Not based on measurement.

---

## 3. Existing Extraction Architecture

### What `extraction_service.py` does

Regex/keyword extraction of: MRP, unit sale price, net quantity, typed dates,
country of origin, batch/lot, manufacturer name + address, consumer care,
commodity name; orchestrated by `run_extraction()`. Unit aliases normalised
(kg→g, l→ml) into a `numeric` comparison value.

### Verified Strengths (PRESERVE)

- `_MRP_RES` patterns tolerate `MRP`, `Rs.`, `₹`, `M.R.P.`, `MRP:` and OCR disfigurements like `MRRP`/`MRF`
- Net-quantity partial fallback: label seen, value/unit unreadable → REVIEW field instead of missing
- Typed-date label mapping (packing/best-before/expiry)
- OCR-typo-tolerant commodity label (`Commedity Name`)
- Country-of-origin handles `Madein India` style merges
- Unit canonicalization (kg→g, l→ml, etc.)
- Consumer care detection with phone/email/website regexes

### Verified Problems

1. **No image/block traceability.** `ExtractedField.source_image_id` and `bbox` are never set — `_persist_extraction()` always writes `extraction_method="regex"` and leaves `source_image_id` NULL. Evidence is text-only.
2. **No field status** (DETECTED/UNCERTAIN/MISSING/CONFLICTING). Missing = key absent, which the rule engine treats as FAIL; no CONFLICTING state at all.
3. **Runs on concatenated cross-image text.** compliance_service joins raw text from all images with `\n` before extraction, so field ↔ image attribution is lost and conflicting values (MRP ₹450 front vs ₹480 back) silently collapse to "first match wins" (`regex.search`).
4. **Confidence is hardcoded** (0.95 MRP, 0.9 net qty, 0.85 manufacturer…), never combined with OCR confidence.
5. **No spatial line reconstruction.** EasyOCR blocks are joined to text by the OCR service's crude clustering; extraction sees a flat string.
6. **Commodity-name heuristic is fragile** — "first reasonable non-label line" is a guess.
7. **`extract_dates` returns raw strings only** (no normalised value), and the `dates` field's `source_text` is hardcoded to `""`.

---

## 4. Existing Endpoints

| Endpoint | Method | Auth | Purpose |
|----------|--------|------|---------|
| `POST /api/v1/analyses` | POST | JWT, not ADMIN | Create analysis container |
| `POST /api/v1/analyses/{id}/images` | POST | JWT, not ADMIN | Upload one image (FRONT/BACK/SIDE/OTHER) |
| `POST /api/v1/analyses/{id}/ocr` | POST | JWT, not ADMIN | Run OCR on all images, persist + return blocks |
| `POST /api/v1/analyses/{id}/run` | POST | JWT, not ADMIN | Full pipeline: OCR → extraction → rules |
| `GET /api/v1/analyses/{id}/report` | GET | JWT | PDF report from persisted results |
| `GET /api/v1/analyses` | GET | JWT | Role-scoped list |

### Verified Coupling Problems

1. **Duplicated OCR+persist logic.** `app/api/analysis.py::run_ocr` (lines 231–285) and `compliance_service._run_ocr_and_persist` (lines 31–61) are near-identical loops.
2. **Dead code.** `compliance_service._ocr_raw_text` (lines 20–28) is defined but never called.
3. **No per-image failure tolerance.** Both OCR loops have no try/except per image — one corrupt image aborts the whole analysis.
4. **Schema mismatch.** `app/schemas/image.py::OCRResponse` declares `image_id`, `processing_time_ms`, `engine`, `steps_applied`, but the endpoint returns a plain dict. The response_model is never applied.
5. **Position model lacks TOP.** `ImagePosition` = FRONT/BACK/SIDE/OTHER only; "top" maps to OTHER.
6. **`run_ocr` re-runs OCR unconditionally** even when OCRResult rows exist (`/run` reuses, `/ocr` does not) — inconsistent caching.

---

## 5. Existing Schemas / Models

### DB Models (`app/models/analysis.py`) — preserve, extend

- `Analysis` — owner, status, category, summary_json. OK.
- `ProductImage` — filename, file_path, mime, position, width/height. OK; no quality columns (optional add later).
- `OCRResult` — per-image raw_text, text_blocks JSON, confidence_score, processing_time_ms, ocr_engine. Already evidence-shaped; no `normalized_text` / `line_count` / `quality` columns yet (optional).
- `ExtractedField` — already has `field_value_numeric`, `source_text`, `source_image_id`, `extraction_method`. Missing `field_status`, `extraction_confidence`, `source_bbox`, `conflict_candidates` (optional adds).

### Pydantic Schemas (`app/schemas/image.py`)

- `ImageMetadata` / `UploadedImageResponse` — used, correct.
- `OCRBlockSchema` — `text/confidence/bbox[x,y,w,h]`.
- `OCRResponse` — **unused and out of sync** with the actual response (see §4).

### Config (`app/core/config.py`)

All spec-required OCR knobs already exist:
- `OCR_LANGUAGE` = ["en"]
- `OCR_GPU` = False
- `OCR_MAX_IMAGE_DIM` = 1800
- `OCR_MIN_CONFIDENCE` = 0.25
- `OCR_DENOISE` = True
- `OCR_ENABLE_DESKEW` = False
- `OCR_ENABLE_THRESHOLD` = False
- `OCR_ENABLE_CLAHE` = False
- `OCR_MIN_IMAGE_WIDTH` = 200
- `OCR_MIN_IMAGE_HEIGHT` = 200
- `OCR_BLUR_THRESHOLD` = 100.0
- `OCR_BRIGHTNESS_LOW` = 0.2
- `OCR_BRIGHTNESS_HIGH` = 0.85
- `OCR_ENABLE_DEBUG` = False
- `OCR_DEBUG_DIR` = Path("debug")

**Only `OCR_LANGUAGE`, `OCR_GPU`, `OCR_MAX_IMAGE_DIM`, `OCR_MIN_CONFIDENCE`, `OCR_DENOISE` are actually read by the old pipeline.** The rest are dead configuration waiting for the new engine.

---

## 6. Current Problems

| # | Problem | Evidence | Severity |
|---|---------|----------|----------|
| P1 | OCR runs 3 passes per image over 6 variants with no measured benefit | `ocr_service._pick_variants`, `MAX_OCR_PASSES=3` | HIGH |
| P2 | No image quality assessment in active pipeline | config thresholds defined but never read by image_service.py | HIGH |
| P3 | No minimum-dimension validation beyond file-level checks | `OCR_MIN_IMAGE_WIDTH/HEIGHT` unused in preprocessing | MEDIUM |
| P4 | Config toggles for deskew/CLAHE/threshold are dead in old pipeline | no code reads them; new preprocessing.py reads them but isn't wired in | HIGH |
| P5 | No text-line reconstruction; extraction consumes flat concatenated text | `_merge_results` clusters only for dedup, not for line grouping | HIGH |
| P6 | No field status (MISSING/UNCERTAIN/CONFLICTING) | extraction returns only present fields | HIGH |
| P7 | No field ↔ image/bbox traceability | `source_image_id` never populated; no bbox stored | HIGH |
| P8 | Conflicting values across images silently collapse | single `regex.search` over joined text | HIGH |
| P9 | One bad image aborts the entire analysis | no try/except in either OCR loop | HIGH |
| P10 | Duplicated OCR+persist logic in API and compliance service | two near-identical loops | MEDIUM |
| P11 | Dead code (`_ocr_raw_text`) and unused schema (`OCRResponse`) | verified by search | LOW |
| P12 | Hardcoded extraction confidence, not combined with OCR confidence | extraction_service constants | MEDIUM |
| P13 | No debug visualization or processed-image output | `OCR_ENABLE_DEBUG` unused | LOW |
| P14 | No structured per-image logging (stage durations, block counts) | no logging in pipeline at all | MEDIUM |
| P15 | Extraction doesn't preserve raw vs normalized text | one `raw_text` column, no normalization step | MEDIUM |
| P16 | New preprocessing module exists but is not wired into pipeline | `image/preprocessing.py` complete, never imported by active code | HIGH |

---

## 7. Root Causes

1. **Variant-bloat by design.** The previous iteration assumed more image representations = better OCR ("six-variant OCR"), without a golden dataset to prove it. Result: 3× the OCR cost, coordinate-rescaling approximation, and fusion bugs that corrupt evidence.
2. **No quality gate.** Without blur/brightness/contrast metrics in the active pipeline, bad images flow straight into OCR and produce low-confidence garbage that extraction regexes misread.
3. **Missing geometry layer.** The engine never reconstructs semantic text lines from block geometry, so "Manufactured / by / ABC Foods / Pvt Ltd" is only recoverable by luck of OCR ordering.
4. **Evidence stripped at the boundary.** `ExtractedField` is written without source image, bbox, or line reference — the exact data needed for conflict detection and audit.
5. **Extraction is text-in, not evidence-in.** It takes a joined string, so per-image provenance and conflicts cannot exist.
6. **Orchestration scattered.** API layer and compliance service each run their own pipeline with inconsistent caching/error behaviour.
7. **Incomplete rebuild.** Phases 1–3 modules exist but the new preprocessing isn't connected; the pipeline still uses the old variant-based code.

---

## 8. Code That Can Be Reused

| Component | Location | Verdict |
|-----------|----------|---------|
| `validate_image_bytes()` | image/validator.py | PRESERVE — Phase 1, tested |
| `quality.assess()` | image/quality.py | PRESERVE — Phase 2, tested |
| `preprocess()` / `preprocess_bytes()` | image/preprocessing.py | PRESERVE — Phase 3, tested, wire into pipeline |
| `decode()` | image/preprocessing.py | PRESERVE — Pillow + EXIF decode |
| `PreprocessedImage` | image/preprocessing.py | PRESERVE — coordinate mapping, steps tracking |
| `_get_reader()` lazy EasyOCR singleton | ocr_service.py:61–73 | MOVE to `ocr/engine.py` |
| `normalize_bbox()` polygon→[x,y,w,h] | ocr_service.py:76–86 | MOVE to `ocr/engine.py` |
| All MRP/quantity/date/manufacturer/country/batch/care/commodity regexes | extraction_service.py | PORT to new extraction module unchanged |
| `ExtractionResult`/`ExtractedField` dataclasses | extraction_service.py | REBUILD as evidence-aware (keep shape for rule engine compat) |
| `run_extraction()` composition | extraction_service.py:371–417 | Split per field, add status/evidence |
| `extraction_to_dict()` | extraction_service.py:420–431 | Adapt to new field model |
| `run_complete_analysis()` | compliance_service.py | Preserve interface; call new pipeline for OCR/extraction |
| DB models | models/analysis.py | Extend with optional nullable columns |
| `generate_fixtures.py` | scripts/ | Preserve; extend for golden dataset |
| Fixture images + tests | tests/fixtures, test_*.py | Preserve and expand |
| Classification service | classification_service.py | PRESERVE — out of scope |
| Compliance engine | app/compliance/ | PRESERVE — out of scope |

---

## 9. Code That Should Be Replaced / Removed

| Component | Location | Action |
|-----------|----------|--------|
| `ImageVariant` / `PreprocessedImage.variants` | image_service.py:33–50, 186–246 | REMOVE — no variant system |
| `_build_variants()` | image_service.py:186–246 | REMOVE — baseline path only |
| `_estimate_skew_angle()` / `_deskew()` / `_clahe_enhance()` | image_service.py:131–183 | REMOVE — duplicated in preprocessing.py |
| Multi-variant selection + fusion | ocr_service.py:89–207 | REPLACE — single-pass OCR + per-block evidence |
| `run_ocr()` shape (grayscale-array fallback) | ocr_service.py:210–260 | REPLACE — image_id-aware pipeline |
| `OCRBlock` / `OCRResult` (no image_id, no raw/normalized) | ocr_service.py:31–50 | REPLACE with evidence-aware models |
| `preprocess()` variant orchestration | image_service.py:249–293 | REPLACE — call image/preprocessing.py instead |
| Flat-string extraction | extraction_service.py | REPLACE with evidence-aware extractors |
| `_ocr_raw_text()` | compliance_service.py:20–28 | DELETE — dead code |
| Duplicated OCR loop in `run_ocr` endpoint | api/analysis.py:231–285 | REPLACE with pipeline call |
| `OCRResponse` schema | schemas/image.py:38–49 | REBUILD to match real output |
| Old `image_service.py` (entire file after migration) | image_service.py | KEEP storage functions (save_upload, ensure_upload_dir), REMOVE preprocessing/variant code |

---

## 10. Proposed New Architecture

```
IMAGE
  ↓
IMAGE VALIDATION          image/validator.py        (PRESERVE — Phase 1 DONE)
  ↓
IMAGE QUALITY ASSESSMENT  image/quality.py          (PRESERVE — Phase 2 DONE)
  ↓
IMAGE PREPROCESSING       image/preprocessing.py    (PRESERVE — Phase 3 DONE, needs wiring)
  ↓                         (decode → resize → grayscale → denoise → CLAHE
  ↓                          → deskew/threshold if configured; original preserved)
OCR                       ocr/engine.py             (BUILD — lazy singleton, single pass,
  ↓                                                 image_id-aware, returns evidence blocks)
RAW OCR EVIDENCE          blocks: id, image_id, text, confidence, bbox, engine
  ↓
OCR NORMALIZATION         ocr/normalizer.py         (BUILD — raw_text + normalized_text)
  ↓
TEXT LINE RECONSTRUCTION  ocr/line_builder.py       (BUILD — geometry grouping → lines)
  ↓
FIELD EXTRACTION          extraction/fields.py      (BUILD — ported regexes, evidence-aware)
  ↓
FIELD NORMALIZATION       extraction/normalizer.py  (BUILD — units, currency, values)
  ↓
CONFIDENCE EVALUATION     extraction/confidence.py  (BUILD — OCR conf × extraction conf)
  ↓
MULTI-IMAGE MERGE         analysis/evidence_merger.py (BUILD — per-image evidence, conflict)
  ↓
EVIDENCE STORAGE/RETURN   analysis/ocr_pipeline.py  (BUILD — orchestrator, logging, error isolation)
  ↓
ENGINE RESULT             → existing compliance_service (rule engine OUT OF SCOPE)
```

### Directory Layout (final)

```
app/services/
  image/
    __init__.py
    validator.py          (Phase 1 — DONE)
    quality.py            (Phase 2 — DONE)
    preprocessing.py      (Phase 3 — DONE, needs wiring)
  ocr/
    __init__.py
    engine.py             (Phase 4 — BUILD)
    normalizer.py         (Phase 5 — BUILD)
    line_builder.py       (Phase 6 — BUILD)
    visualization.py      (Phase 12 — BUILD, debug only)
  extraction/
    __init__.py
    fields.py             (Phase 7 — BUILD, ported regexes)
    normalizer.py         (Phase 8 — BUILD)
    evidence.py           (Phase 9 — BUILD)
    confidence.py         (Phase 9 — BUILD)
  analysis/
    __init__.py
    ocr_pipeline.py       (Phase 13 — BUILD, orchestrator)
    evidence_merger.py    (Phase 10/11 — BUILD, conflict detection)
```

### Key Design Decisions

- **Single baseline pass**: original → decode → orientation → resize → light denoise → contrast-if-needed → EasyOCR. No variants until testing proves an extra operation helps. Original bytes always preserved.
- **Never destroy raw OCR**: every block keeps `raw_text` + `normalized_text`.
- **Evidence-first**: fields carry `source_text`, `bbox`, `image_id`, `ocr_confidence`, `extraction_confidence`, `status` (DETECTED/UNCERTAIN/MISSING/CONFLICTING).
- **Per-image isolation**: one failed image → marked failed, others proceed.
- **No compliance decisions** anywhere in this engine.
- **Deterministic only** for now; interfaces designed so AI-assisted extraction can slot in later without schema/rule-engine changes.

---

## 11. Implementation Phases

| Phase | Description | Primary files | Status |
|-------|-------------|---------------|--------|
| 0 | Audit (this document) | docs/OCR_ENGINE_AUDIT.md | **COMPLETE** |
| 1 | Image validation | `image/validator.py` | **COMPLETE** |
| 2 | Image quality assessment | `image/quality.py` | **COMPLETE** |
| 3 | Baseline preprocessing | `image/preprocessing.py` | **COMPLETE** (not wired) |
| 4 | EasyOCR engine (single pass, lazy singleton) | `ocr/engine.py` | **COMPLETE** |
| 5 | OCR normalization (raw vs normalized) | `ocr/normalizer.py` | **COMPLETE** |
| 6 | Text line reconstruction | `ocr/line_builder.py` | **COMPLETE** |
| 7 | Deterministic field extraction (ported regexes) | `extraction/fields.py` | **COMPLETE** |
| 8 | Field normalization | `extraction/normalizer.py` | **COMPLETE** |
| 9 | Evidence + confidence model | `extraction/evidence.py`, `extraction/confidence.py` | **COMPLETE** |
| 10 | Multi-image evidence merging | `analysis/evidence_merger.py` | **COMPLETE** |
| 11 | Conflict detection (CONFLICTING status) | `analysis/evidence_merger.py` | **COMPLETE** |
| 12 | Debug visualization (`draw_ocr_boxes`) | `ocr/visualization.py` | **COMPLETE** |
| 13 | End-to-end orchestrator + API wiring | `analysis/ocr_pipeline.py`, `api/analysis.py`, `compliance_service.py` | **COMPLETE** |
| 14 | Performance measurement (per-stage timing) | `analysis/ocr_pipeline.py` timings | **COMPLETE** |
| 15 | Golden dataset evaluation | `tests/fixtures/ocr/expected/*.json`, `scripts/evaluate_golden.py` | **COMPLETE** |

All phases complete and the engine is wired into the live pipeline. Full
suite: 146 tests.

Each phase ends with: summary, file list, test run, failure analysis, documentation update, then STOP for review.

---

## 12. Tests Currently Available

146 test functions across 14 files (verified from source):

| File | Count | Covers |
|------|-------|--------|
| `tests/test_ocr.py` | 10 | Validation (valid/empty/non-image/oversized), preprocessing dims, OCR structure, bbox normalization |
| `tests/test_extraction.py` | 8 | Full label, missing-not-invented, net-weight REVIEW fallback, best-before duration, OCR-typo commodity, country, empty evidence, aggregate priority |
| `tests/test_image_validator.py` | 12 | Phase 1: valid/empty/corrupt/oversized/unsupported/tiny images, path-based, backward compat |
| `tests/test_quality.py` | 12 | Phase 2: GOOD/blur/dark/bright/low-contrast/blank/tiny, to_dict, bytes, BGR, empty |
| `tests/test_preprocessing.py` | 16 | Phase 3: decode/EXIF/baseline shapes/bytes/no-BGR/original preservation/bbox mapping/resize/denoise/CLAHE/deskew/threshold/options |
| `tests/test_ocr_engine.py` | 10 | Phase 4: single-pass engine evidence contract, raw/normalized, empty→OCR_NO_TEXT, reader singleton |
| `tests/test_ocr_engine_phases.py` | 8 | Phases 5/6/12: normalizer, line_builder, visualization |
| `tests/test_extraction_evidence.py` | 13 | Phases 7-11+15: fields, normalizer, confidence, merger, conflict, golden |
| `tests/test_pipeline_evidence.py` | 3 | Phases 13/14: end-to-end /run, DB evidence persistence, timings |
| `tests/test_analysis_api.py` | 9 | Create/upload/OCR endpoints, invalid position, non-image, no-images, missing analysis, auth, listing |
| `tests/test_compliance_pipeline.py` | 4 | Full pipeline, PDF report, report-without-run, missing-declarations FAIL |
| `tests/test_auth_rbac.py` | 20 | Login/register/RBAC/zone/product/inspection/dashboard/analysis ownership |
| `tests/test_models.py` | 6 | Model registration, tables, columns, FKs, repr |
| `tests/test_system.py` | 8 | Health/version/readiness endpoints, OpenAPI |

---

## 13. Missing Tests (all now covered by the completed rebuild)

| Category | Tests | File |
|----------|-------|------|
| OCR engine | block shape (image_id, raw/normalized), confidence range, engine label, empty → OCR_NO_TEXT | tests/test_ocr_engine.py |
| Line reconstruction | multi-line grouping, ordering, block↔line links | tests/test_ocr_engine_phases.py |
| Extraction | MRP, Net Wt., batch, country; currency/decimal normalisation; no-MRP-context reject | tests/test_extraction_evidence.py + golden |
| Confidence | high/low OCR conf propagation, missing field, uncertain field | tests/test_extraction_evidence.py |
| Multi-image | front+back merge, MRP 450 vs 480 → CONFLICTING | tests/test_extraction_evidence.py |
| Debug | draw_ocr_boxes output shape, disabled no-op | tests/test_ocr_engine_phases.py |
| End-to-end | evidence + fields + confidence + source refs through /run | tests/test_pipeline_evidence.py |
| Performance | per-stage timing recorded | tests/test_pipeline_evidence.py |
| Golden dataset | expected JSON comparisons + accuracy metrics | scripts/evaluate_golden.py + test_golden_dataset_extraction_accuracy |

---

## 14. Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| Breaking existing API responses / frontend | HIGH | Keep response keys, add new ones; run API tests each phase |
| Breaking rule-engine contract (`ExtractionResult` shape) | HIGH | Keep `fields` dict keyed by field name; extend, don't rename |
| EasyOCR regression vs old fusion path | MEDIUM | Golden dataset comparison before/after; single pass is cheaper, must not be worse |
| Extraction regex regressions | LOW | Port regexes verbatim first, then restructure |
| DB schema drift | LOW | Add optional nullable columns; no destructive migration |
| Performance (CPU OCR) | MEDIUM | Lazy singleton, single pass, measure per stage |

---

## 15. Testing Strategy

1. Fix any local pytest issues and establish a clean baseline run (89 tests) before touching production code.
2. Unit-test each new module in isolation (engine, normalizer, line_builder, fields, evidence, confidence).
3. Port every existing extraction test to the new field model; add the spec-exact examples from §13.
4. Build `tests/fixtures/ocr/expected/*.json` golden files from the synthetic fixtures first, then from the real photos, and record honest accuracy numbers.
5. End-to-end: front + back image through the orchestrator, asserting evidence traceability, statuses, and per-image failure tolerance.
6. Performance: record preprocessing / OCR / extraction / total per image and document in `OCR_ENGINE.md`.

---

## 16. Conclusion

The foundation is solid: validation (Phase 1), quality assessment (Phase 2), and preprocessing (Phase 3) are implemented and tested but not wired into the main pipeline. The extraction regexes are well-crafted and cover the project's needs.

The rebuild must:
1. **Wire in the existing preprocessing module** (Phase 3 already exists, just needs integration)
2. **Replace the 6-variant/3-pass OCR** with a single-pass engine that returns evidence blocks with image_id
3. **Add text line reconstruction** from bounding box geometry
4. **Carry image_id/bbox/status/confidence** through every extracted field
5. **Merge multi-image evidence** with conflict detection
6. **Isolate per-image failures** so one bad image doesn't abort the analysis
7. **Add debug visualization** for development
8. **Build an orchestrator** that replaces the duplicated logic in api/analysis.py and compliance_service.py

**Engine scope boundary (unchanged):** this engine produces evidence only. It never outputs a compliance decision.
