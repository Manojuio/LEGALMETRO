# OCR Engine

Master documentation for the rebuilt image → OCR → field-extraction engine.

**Key principle:** this engine produces **evidence only**. It never decides
legal compliance. The existing compliance/rule engine consumes the evidence.

**Key principle 2:** the original image is never overwritten. Every piece of
extracted evidence is traceable back to its source image, OCR block, text
line, and confidence.

---

## Target pipeline (logical stages)

```
IMAGE
  ↓
IMAGE VALIDATION          image/validator.py        (Phase 1 — DONE)
  ↓
IMAGE QUALITY ASSESSMENT  image/quality.py          (Phase 2)
  ↓
IMAGE PREPROCESSING       image/preprocessing.py    (Phase 3)
  ↓
OCR                       ocr/engine.py             (Phase 4)
  ↓
RAW OCR EVIDENCE          blocks: id, image_id, text, confidence, bbox
  ↓
OCR NORMALIZATION         ocr/normalizer.py         (Phase 5)
  ↓
TEXT LINE RECONSTRUCTION  ocr/line_builder.py       (Phase 6)
  ↓
FIELD EXTRACTION          extraction/fields.py      (Phase 7)
  ↓
FIELD NORMALIZATION       extraction/normalizer.py  (Phase 8)
  ↓
CONFIDENCE EVALUATION     analysis/confidence.py    (Phase 9)
  ↓
EVIDENCE STORAGE/RETURN   analysis/ocr_pipeline.py  (Phase 13)
  ↓
ENGINE RESULT             → compliance/rule engine  (OUT OF SCOPE)
```

Each responsibility has its own module. No module mixes validation,
preprocessing, OCR, extraction, or confidence logic.

---

## Stable error codes

Raised by engine components, propagated to callers/API:

| Code | Meaning |
|------|---------|
| `INVALID_IMAGE` | empty payload / unsupported format |
| `IMAGE_DECODE_FAILED` | bytes are not a decodable image (corrupt/truncated) |
| `IMAGE_TOO_LARGE` | exceeds `MAX_UPLOAD_SIZE_MB` |
| `IMAGE_TOO_SMALL` | below `OCR_MIN_IMAGE_WIDTH` × `OCR_MIN_IMAGE_HEIGHT` |
| `IMAGE_NOT_FOUND` | stored file missing/unreadable |
| `IMAGE_QUALITY_LOW` | reserved — pipeline gating when an UNUSABLE image reaches OCR (Phase 13) |
| `OCR_FAILED` / `OCR_NO_TEXT` | OCR engine failures (Phase 4) |
| `EXTRACTION_FAILED` | extraction failures (Phase 7) |

---

## Components

### image/quality.py — Phase 2 (COMPLETE)

Deterministic, OpenCV-only quality assessment. Classifies an image as
GOOD / ACCEPTABLE / POOR / UNUSABLE and never silently rejects borderline
images — it returns warnings and the caller decides.

**Purpose:** measure resolution, sharpness, brightness, and contrast so the
pipeline can warn about degraded images before (and alongside) OCR.

**Functions / classes:**

| Name | Input | Output |
|------|-------|--------|
| `assess(image)` | decoded ndarray (BGR or grayscale) | `ImageQuality` |
| `assess_bytes(data)` | raw image bytes (decode + assess) | `ImageQuality` |
| `ImageQuality` | — | dataclass: grade, usable, width, height, megapixels, blur_score, brightness_score, contrast_score, warnings; `.to_dict()` |

**Metrics (deterministic):**
- `blur_score` — variance of the Laplacian (higher = sharper); below
  `OCR_BLUR_THRESHOLD` warns, below 50%/25% of it degrades to POOR/UNUSABLE
- `brightness_score` — mean grayscale luminance in 0..1; banded around
  `OCR_BRIGHTNESS_LOW` / `OCR_BRIGHTNESS_HIGH`, hard floors at 0.05 / 0.97
- `contrast_score` — (P98 − P2) / 255 robust percentile spread; bands
  0.50 / 0.25 / 0.12 (module constants, calibrate with real photos in
  Phase 15)
- resolution — width/height/megapixels; below the configured minimums adds
  a warning and caps the grade at POOR (the validator is the hard gate)

**Design decisions:**
- Worst metric wins (`GOOD < ACCEPTABLE < POOR < UNUSABLE`).
- `usable == grade != UNUSABLE`; POOR images remain usable so OCR can still
  run with a warning.
- Grading is pure and config-driven for blur/brightness thresholds.

**Known limitations:** percentile contrast can read high on noisy images;
no perspective/angle measure yet; blur metric is global, not per-region.

### image/validator.py — Phase 1 (COMPLETE)

Dedicated image validation. Single source of truth; nothing reaches OCR
unvalidated.

**Purpose:** reject invalid images with clear errors before any vision work.

**Functions / classes:**

| Name | Input | Output |
|------|-------|--------|
| `ImageValidationError` | `(code, message)` or legacy `(message)` | exception carrying stable `.code` + `.message` |
| `validate_image_bytes(data, filename=None)` | raw bytes | metadata dict `{width, height, format, mime_type, size_bytes, filename}` |
| `validate_image_file(path)` | path to stored image | same metadata dict (adds file-existence check) |
| constants `INVALID_IMAGE`, `IMAGE_DECODE_FAILED`, `IMAGE_TOO_LARGE`, `IMAGE_TOO_SMALL`, `IMAGE_NOT_FOUND` | — | stable codes |

**Checks (in order):**
1. non-empty payload → `INVALID_IMAGE`
2. size ≤ `MAX_UPLOAD_SIZE_MB` → `IMAGE_TOO_LARGE`
3. full Pillow decode (corruption surfaces here) → `IMAGE_DECODE_FAILED`
4. decoded format in `ALLOWED_IMAGE_TYPES` → `INVALID_IMAGE`
5. width/height ≥ 1 and ≥ `OCR_MIN_IMAGE_WIDTH` × `OCR_MIN_IMAGE_HEIGHT` → `IMAGE_TOO_SMALL`

**Dependencies:** `app.core.config`, Pillow.

**Design decisions:**
- Size check before decode — never decode oversized payloads.
- Format check uses the *decoded container format* (trusts content, not the
  caller's filename/content-type).
- Legacy `ImageValidationError(message)` single-arg form still works, so
  pre-existing raise sites did not need rewriting.
- `image_service.validate_image_bytes` now delegates here (re-exported error
  class keeps all existing callers/tests working unchanged).

**Known limitations:** animated/multi-frame formats are not examined beyond
first frame; EXIF orientation is respected later during decode/preprocessing
(Phase 3), not here.

### ocr/engine.py — Phase 4 (COMPLETE)

Single-pass EasyOCR engine with full evidence traceability.

**Purpose:** run EasyOCR exactly once over one preprocessed grayscale image and
return evidence-first blocks carrying source `image_id` and raw/normalized text.

**Functions / classes:**

| Name | Input | Output |
|------|-------|--------|
| `run_ocr(image_data, image_id="")` | `PreprocessedImage` (uses `.processed`) or grayscale/BGR ndarray | `OCREngineResult` |
| `normalize_bbox(points)` | EasyOCR 4-corner polygon | `[x, y, w, h]` |
| `OCRBlock` | — | `image_id, text, confidence, bbox, engine, raw_text, normalized_text` |
| `OCREngineResult` | — | `blocks, raw_text, normalized_text, confidence_score, processing_time_ms, engine, block_count` |
| `OCRNoTextError` / `OCREngineError` | — | typed errors with stable `.code` (`OCR_NO_TEXT` / `OCR_FAILED`) |

**Design decisions:**
- Single pass: no 6-variant / 3-pass fusion (audit P1, P16). An extra pass is
  only re-added if a golden dataset proves it helps (Phase 15).
- Lazy singleton reader (`_get_reader`) moved from `ocr_service.py`.
- Every block is evidence: raw (verbatim) and normalized text are both kept.
- Blank OCR → `OCRNoTextError(OCR_NO_TEXT)`; empty/corrupt input →
  `OCREngineError(OCR_FAILED)`.
- Never emits a compliance verdict.

**Wired in:** the live `/run` and `/ocr` paths now route through this engine via
the Phase 13 orchestrator (`app/services/analysis/ocr_pipeline.py`). The legacy
`ocr_service.run_ocr` is superseded but kept for backward compatibility.

### ocr/normalizer.py — Phase 5 (COMPLETE)

Turns each raw OCR block into a `NormalizedBlock` keeping verbatim `raw_text`
plus cleaned `normalized_text`. Non-destructive whitespace collapse + noise-token
stripping. Never fabricates.

### ocr/line_builder.py — Phase 6 (COMPLETE)

Reconstructs semantic text lines from block geometry (vertical-center band
grouping, left-to-right ordering). `build_lines` / `join_lines` /
`sort_lines_by_top`. Each `TextLine` keeps its member blocks for provenance.

### ocr/visualization.py — Phase 12 (COMPLETE)

`draw_ocr_boxes` writes an annotated PNG under `OCR_DEBUG_DIR` only when
`OCR_ENABLE_DEBUG=True`. Debug only; never affects evidence.

### extraction/fields.py — Phase 7 (COMPLETE)

Ported regex extractors (`extract_fields` over reconstructed lines), producing
evidence-aware `FieldEvidence` with image_id/bbox/status. Net-quantity
label-without-value → UNCERTAIN. Manufacturer/address regexes use
`re.MULTILINE` per the legacy implementation.

### extraction/normalizer.py — Phase 8 (COMPLETE)

Value normalization: `canonical_unit`, `normalize_quantity` (kg→g, l→ml),
`parse_number`, `strip_currency`, `is_price_context`, `normalize_due_date`.

### extraction/evidence.py + confidence.py — Phase 9 (COMPLETE)

`FieldStatus` (DETECTED/UNCERTAIN/MISSING/CONFLICTING), `FieldEvidence`,
`FieldCollection`. `combine()` = OCR confidence × extractor confidence
(cap 0.95); `field_status()` derives status from presence/confidence.

### analysis/evidence_merger.py — Phases 10 & 11 (COMPLETE)

`merge_collections` (per-image → per-field), `resolve_conflicts`
(scalar fields with differing normalized values → CONFLICTING).

### analysis/ocr_pipeline.py — Phases 13 & 14 (COMPLETE)

`run_pipeline` orchestrates validate → quality → preprocess → single-pass OCR →
normalize → build lines → extract → merge/conflict, persists OCRResult +
source-image-aware ExtractedField rows, isolates per-image failures, and records
per-stage timings. Wired into `compliance_service.run_complete_analysis` and the
`/ocr` endpoint (duplicate loop removed).

---

## Rebuild phase status

| Phase | Description | Status | Date |
|-------|-------------|--------|------|
| 0 | Audit existing implementation | COMPLETE | 2026-09-03 |
| 1 | Image validation | COMPLETE | 2026-09-03 |
| 2 | Image quality assessment | COMPLETE | 2026-09-03 |
| 3 | Baseline preprocessing | COMPLETE | 2026-09-03 |
| 4 | EasyOCR engine | COMPLETE | 2026-09-03 |
| 5 | OCR normalization | COMPLETE | 2026-09-03 |
| 6 | Text line reconstruction | COMPLETE | 2026-09-03 |
| 7 | Deterministic field extraction | COMPLETE | 2026-09-03 |
| 8 | Field normalization | COMPLETE | 2026-09-03 |
| 9 | Evidence + confidence | COMPLETE | 2026-09-03 |
| 10 | Multi-image evidence merging | COMPLETE | 2026-09-03 |
| 11 | Conflict detection | COMPLETE | 2026-09-03 |
| 12 | Debug visualization | COMPLETE | 2026-09-03 |
| 13 | End-to-end pipeline | COMPLETE | 2026-09-03 |
| 14 | Performance measurement | COMPLETE | 2026-09-03 |
| 15 | Golden dataset evaluation | COMPLETE | 2026-09-03 |

The engine rebuild is now COMPLETE. The orchestrator in
`app/services/analysis/ocr_pipeline.py` is wired into `compliance_service`
and the `/ocr` endpoint; unit + integration + golden-dataset validation are
covered by the test suite (146 tests).

---

## Known engine-wide limitations

- **Extraction-layer accuracy** is measured on the project's golden dataset
  (deterministic extractors: 100% on `tests/fixtures/ocr/expected/fields.json`).
- **OCR accuracy** (EasyOCR over real photos) is non-deterministic run-to-run and
  is not claimed generally; confidence values are evidence, not guarantees.
- This engine never outputs a compliance verdict.
