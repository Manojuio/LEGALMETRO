# API Documentation

This document tracks all API endpoints. Maintained by the AI on every endpoint change.

---

## GET /health

### Purpose

Root-level health check. Alias for `GET /api/v1/health` exposed at the root path.

### Authentication

Required: No

### Roles

Any (public)

### Input

None

### Output

200:
```json
{
  "status": "ok",
  "app": "Packaged Commodities Compliance Scanner",
  "version": "0.1.0"
}
```

### Errors

None

### Database changes

None

---

## GET /api/v1

### Purpose

Informational root for the API v1 namespace. Lists available endpoints.

### Authentication

Required: No

### Roles

Any (public)

### Input

None

### Output

200:
```json
{
  "name": "Packaged Commodities Compliance Scanner",
  "version": "0.1.0",
  "endpoints": ["/api/v1/health", "/api/v1/version"]
}
```

### Errors

None

### Database changes

None

---

## GET /api/v1/health

### Purpose

Application health check. Returns status, app name, and version.

### Authentication

Required: No

### Roles

Any (public)

### Input

None

### Output

200:
```json
{
  "status": "ok",
  "app_name": "Packaged Commodities Compliance Scanner",
  "version": "0.1.0"
}
```

### Errors

None

### Database changes

None

### Tests

- `tests/test_system.py::test_health_check`

---

## GET /api/v1/health/live

### Purpose

Liveness probe. The process is considered alive if this returns 200.

### Authentication

Required: No

### Roles

Any (public)

### Input

None

### Output

200:
```json
{
  "status": "alive",
  "app_name": "Packaged Commodities Compliance Scanner",
  "version": "0.1.0"
}
```

### Errors

None

### Database changes

None

### Tests

- `tests/test_system.py::test_liveness`

---

## GET /api/v1/health/ready

### Purpose

Readiness probe. Verifies the PostgreSQL connection is reachable.

### Authentication

Required: No

### Roles

Any (public)

### Input

None

### Processing

1. Open database session
2. Execute `SELECT 1`
3. Close session
4. Return ready status or 503 on failure

### Output

200:
```json
{
  "status": "ready",
  "database": "connected",
  "app": "Packaged Commodities Compliance Scanner",
  "version": "0.1.0"
}
```

### Errors

- 503: Database unavailable

### Database changes

None (read-only connection check)

### Tests

- `tests/test_system.py::test_readiness`

---

## GET /api/v1/version

### Purpose

Returns API name and version information.

### Authentication

Required: No

### Roles

Any (public)

### Input

None

### Output

200:
```json
{
  "name": "Packaged Commodities Compliance Scanner",
  "version": "0.1.0",
  "docs_url": "/docs"
}
```

### Errors

None

### Database changes

None

### Tests

- `tests/test_system.py::test_version_endpoint`

---

## POST /api/v1/analyses

### Purpose

Create a new analysis (the container for a product compliance scan).

### Authentication

Required: No (public in current phase — auth added in Phase 6)

### Roles

Any

### Input

Form fields (optional):
- `category`: string
- `subcategory`: string

### Output

201:
```json
{
  "analysis_id": "uuid",
  "status": "PENDING"
}
```

### Errors

- 400: No analysis owner available

### Database changes

Creates an `analyses` row.

### Tests

- `tests/test_analysis_api.py::test_create_analysis`

---

## POST /api/v1/analyses/{analysis_id}/images

### Purpose

Upload one product image to an analysis. Validates the file and stores it on
disk; only metadata is persisted in the database.

### Authentication

Required: No (currently public)

### Roles

Any

### Input

Multipart form:
- `file`: binary image (JPEG/PNG/WebP, ≤10MB)
- `position`: FRONT | BACK | SIDE | OTHER

### Processing

1. Load analysis
2. Validate file (empty, size, MIME, decodability)
3. Store binary under `uploads/analysis_<id>/`
4. Create `ProductImage` row
5. Mark analysis as PROCESSING

### Output

201:
```json
{
  "analysis_id": "uuid",
  "image": {
    "id": "uuid",
    "filename": "front.jpg",
    "file_path": "uploads/analysis_.../front.jpg",
    "file_size": 12345,
    "mime_type": "image/jpeg",
    "image_position": "FRONT",
    "width": 900,
    "height": 1200
  }
}
```

### Errors

- 404: Analysis not found
- 422: Invalid position / unsupported type / over size limit / corrupt image

### Database changes

Creates a `product_images` row; updates `analyses.status`.

### Tests

- `tests/test_analysis_api.py::test_upload_image_and_ocr`
- `tests/test_analysis_api.py::test_upload_invalid_position`
- `tests/test_analysis_api.py::test_upload_non_image`
- `tests/test_analysis_api.py::test_upload_missing_analysis`

---

## POST /api/v1/analyses/{analysis_id}/ocr

### Purpose

Run the full OCR pipeline on all images attached to the analysis. Persists
OCR results as evidence. Does NOT make compliance decisions.

### Authentication

Required: No (currently public)

### Roles

Any

### Input

Path: `analysis_id`

### Processing

1. Load analysis
2. Load all `ProductImage` rows
3. For each image: read bytes → preprocess → EasyOCR
4. Normalize blocks (text, confidence, [x,y,w,h])
5. Persist an `OCRResult` row per image
6. Aggregate across images

### Output

200:
```json
{
  "status": "completed",
  "analysis_id": "uuid",
  "text_blocks": [
    {"image_id": "...", "position": "FRONT", "text": "...", "confidence": 0.98, "bbox": [x,y,w,h]}
  ],
  "raw_text": "...",
  "confidence": 0.82,
  "image_count": 1
}
```

### Errors

- 404: Analysis not found
- 400: No images uploaded to this analysis

### Database changes

Creates `ocr_results` rows.

### Tests

- `tests/test_analysis_api.py::test_upload_image_and_ocr`
- `tests/test_analysis_api.py::test_ocr_no_images`
- `tests/test_analysis_api.py::test_ocr_missing_analysis`

### AI involvement

None in decision logic. EasyOCR is a machine-learning model for text
recognition only.

### Limitations

- OCR confidence is evidence, not proof of compliance
- Accuracy measured on our own dataset only
- Physical quantity can never be verified from an image
