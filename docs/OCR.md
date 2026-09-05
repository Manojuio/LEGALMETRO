# OCR Pipeline

This document describes the OCR subsystem built in Phase 9.

**Key principle:** OCR is evidence extraction, NOT legal decision-making.
The Rule Engine decides compliance from structured data that OCR *feeds*.

---
## Pipeline

```
Image bytes
   │
   ▼
Image Validation          (type, size, integrity)
   │
   ▼
Image Preprocessing       (decode → resize → denoise → adaptive threshold)
   │
   ▼
EasyOCR                   (text + confidence + bounding boxes)
   │
   ▼
Normalized OCR Blocks     ([x, y, w, h], confidence, text)
   │
   ▼
Persist as evidence       (ocr_results table)
```

## Files

| File | Responsibility |
|------|----------------|
| `app/services/image_service.py` | Validation + preprocessing + storage |
| `app/services/ocr_service.py` | EasyOCR invocation + normalization |
| `app/api/analysis.py` | Upload + OCR endpoints |
| `app/schemas/image.py` | API request/response schemas |
| `scripts/generate_fixtures.py` | Synthetic fixture image generator |
| `tests/fixtures/*.jpg` | Test images |
| `tests/test_ocr.py` | Unit tests |
| `tests/test_analysis_api.py` | API integration tests |

## Endpoints

### POST /api/v1/analyses
Create an analysis. Returns `analysis_id`.

### POST /api/v1/analyses/{analysis_id}/images
Upload one image. Multipart form: `file` (binary) + `position` (FRONT/BACK/SIDE/OTHER).
Validates MIME type, size limit, decodability. Stores binary on disk under
`uploads/analysis_<id>/`. Only metadata is persisted in `product_images`.

### POST /api/v1/analyses/{analysis_id}/ocr
Runs the full OCR pipeline on every image attached to the analysis.
Persists per-image `OCRResult` rows. Response:

```json
{
  "status": "completed",
  "analysis_id": "...",
  "text_blocks": [
    {
      "image_id": "...",
      "position": "FRONT",
      "text": "Net Wt. 500 g",
      "confidence": 0.98,
      "bbox": [80, 210, 300, 60]
    }
  ],
  "raw_text": "...",
  "confidence": 0.82,
  "image_count": 1
}
```

## Preprocessing steps

1. **Decode + EXIF normalize** (Pillow → OpenCV BGR)
2. **Resize** if the longest edge exceeds `OCR_MAX_IMAGE_DIM` (default 1800), preserving aspect ratio
3. **Denoise** — `fastNlMeansDenoising` (h=10) to reduce sensor noise on photos
4. **Adaptive threshold** — Gaussian adaptive to binarize and boost contrast for text

Each step is recorded in `steps_applied` so the output is auditable.

## EasyOCR configuration

- Reader created lazily and cached (module-level singleton) — model loads once per process
- Language: `["en"]` (from `OCR_LANGUAGE`)
- GPU: off by default (`OCR_GPU=False`) — local CPU
- Output normalized: EasyOCR polygons → `[x, y, w, h]`

## Known weaknesses

- Photos taken at an angle / curved packaging reduce accuracy
- Small or low-contrast text may be missed
- Font size is NOT measured precisely — visual rules must return REVIEW when uncertain
- Physical dimensions cannot be measured from arbitrary photos (Rule 7/8/9 limitations)

## Measured accuracy (our dataset only)

We do NOT claim a general accuracy figure. The numbers below are from our
OWN synthetic fixture images and will differ on real photos.

On `tests/fixtures/valid_tea.jpg` (8 text lines):
- All 8 lines recognized
- Aggregate confidence: **0.82**

On subsequent runs the first real-photo batch will be measured and recorded
here, not assumed.

## OCR failures

OCR is non-deterministic — the same image can produce slightly different
text/confidence between runs. Low-confidence blocks are retained with their
confidence value; downstream validators flag them for human review rather
than silently trusting them.

## Execution time

- First call per process: ~120s (model download + load on first ever run)
- Subsequent calls: ~seconds per image on CPU
- Tests measure with `processing_time_ms` recorded per image
