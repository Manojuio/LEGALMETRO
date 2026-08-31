# Data Flow

## Overview

This document describes how data flows through the Packaged Commodities Compliance Scanner system, from image upload to compliance report.

## Primary Data Flow

### Phase 1: Image Upload

```
User selects images (1-3)
    │
    ▼
Frontend validates:
  - File type (JPEG, PNG, WebP)
  - File size (< 10MB)
  - Resolution (> 640x480)
    │
    ▼
POST /api/v1/analyses/{id}/images
    │
    ▼
Backend validates:
  - File type
  - File size
  - Image integrity
    │
    ▼
Save to: uploads/analysis_{id}/{position}.jpg
    │
    ▼
Store metadata in product_images table:
  - filename
  - file_path
  - file_size
  - mime_type
  - image_position (front/back/side)
  - width, height
    │
    ▼
Return: { image_id, position, url }
```

### Phase 2: OCR Processing

```
POST /api/v1/analyses/{id}/ocr
    │
    ▼
Load images from database
    │
    ▼
For each image:
  │
  ├─→ Load image file
  │
  ├─→ Preprocess:
  │     - Resize (max 2000px)
  │     - Denoise
  │     - Contrast enhancement
  │     - Grayscale conversion
  │
  ├─→ EasyOCR processing:
  │     - Text detection
  │     - Text recognition
  │     - Confidence scoring
  │     - Bounding box extraction
  │
  └─→ Normalize OCR output:
        - Text blocks with coordinates
        - Confidence scores
        - Bounding boxes
    │
    ▼
Store in ocr_results table:
  - raw_text
  - text_blocks (JSON array)
  - confidence_score
  - processing_time_ms
  - ocr_engine_version
    │
    ▼
Return: { text_blocks: [...] }
```

### Phase 3: Information Extraction

```
POST /api/v1/analyses/{id}/extract
    │
    ▼
Load OCR results
    │
    ▼
Apply extraction pipelines:
  │
  ├─→ MRP Extraction:
  │     - Pattern: "MRP.*?(\d+\.?\d*)"
  │     - Pattern: "Rs\.?\s*(\d+\.?\d*)"
  │     - Pattern: "₹\s*(\d+\.?\d*)"
  │
  ├─→ Quantity Extraction:
  │     - Pattern: "Net\s*(?:Wt\.?|Qty\.?|Quantity)\s*:?\s*(\d+\.?\d*)\s*(g|kg|ml|l|nos)"
  │
  ├─→ Date Extraction:
  │     - Pattern: "(?:Mfg\.?|Manufactured|Packed)\s*:?\s*(\d{2}[/\-]\d{2}[/\-]\d{4})"
  │     - Pattern: "(?:Best Before|Use By|Expiry)\s*:?\s*(\d{2}[/\-]\d{2}[/\-]\d{4})"
  │
  ├─→ Manufacturer Extraction:
  │     - Pattern: "(?:Manufactured|Packed|Marketed)\s*(?:by|at)\s*:?\s*(.+?)(?:\n|$)"
  │     - Address extraction following manufacturer name
  │
  ├─→ Consumer Care Extraction:
  │     - Pattern: "(?:Consumer Care|Customer Care|Helpline)\s*:?\s*(.+?)(?:\n|$)"
  │     - Phone/email/website extraction
  │
  └─→ Product Name Extraction:
        - Largest text block analysis
        - Common product name patterns
    │
    ▼
Store in extracted_fields table:
  - field_name
  - field_value
  - confidence
  - source_text
  - source_image_id
  - extraction_method
    │
    ▼
Return: { fields: { mrp: 450, net_quantity: { value: 500, unit: "g" }, ... } }
```

### Phase 4: Product Classification

```
POST /api/v1/analyses/{id}/classify
    │
    ▼
Load extracted fields + OCR text
    │
    ▼
Classification pipeline:
  │
  ├─→ Keyword matching against categories.json
  │     - "tea" → FOOD > FOOD_BEVERAGES
  │     - "shampoo" → COSMETIC > COS_HAIR
  │
  ├─→ Category confidence scoring
  │
  └─→ Subcategory determination
    │
    ▼
Store classification result:
  - category
  - subcategory
  - confidence
    │
    ▼
Return: { category: "FOOD", subcategory: "FOOD_BEVERAGES", confidence: 0.91 }
```

### Phase 5: Applicability Determination

```
POST /api/v1/analyses/{id}/applicability
    │
    ▼
Load product category + subcategory
    │
    ▼
Determine applicable rules:
  │
  ├─→ Base rules (apply to all products)
  │     - Rule 3, 4, 5, 6, 10, 11
  │
  ├─→ Category-specific rules from categories.json
  │     - FOOD → quantity rules
  │     - etc.
  │
  ├─→ Package type considerations
  │     - Retail vs non-retail
  │
  └─→ Check exemptions
        - Export
        - Institutional
        - etc.
    │
    ▼
Return: { applicable_rules: ["3", "4", "5", "6", "7", "8", "9", "10", "11", "12", "13", "15"] }
```

### Phase 6: Compliance Validation

```
POST /api/v1/analyses/{id}/validate
    │
    ▼
Load applicable rules + extracted fields
    │
    ▼
For each applicable rule:
  │
  ├─→ Load rule definition
  │
  ├─→ Select validator based on validation_type
  │     - FIELD_PRESENT → declaration validator
  │     - UNIT_VALIDATION → unit validator
  │     - QUANTITY_VALIDATION → quantity validator
  │     - etc.
  │
  ├─→ Run validator:
  │     validator.validate(
  │       product=product,
  │       extracted_data=extracted_fields,
  │       context=analysis_context
  │     )
  │
  ├─→ Validator returns:
  │     {
  │       status: PASS|FAIL|REVIEW|NOT_APPLICABLE,
  │       reason: "Explanation",
  │       evidence: [...],
  │       confidence: 0.95
  │     }
  │
  └─→ Store result
    │
    ▼
Aggregate results:
  - pass: 8
  - fail: 1
  - review: 2
  - not_applicable: 3
    │
    ▼
Determine overall status:
  - Any FAIL → overall FAIL
  - Any REVIEW → overall REVIEW
  - All PASS → overall PASS
    │
    ▼
Return: { overall_status: "REVIEW", rules: [...], summary: {...} }
```

### Phase 7: Evidence Generation

```
For each rule result:
  │
  ├─→ Link to source OCR blocks
  │
  ├─→ Link to bounding boxes
  │
  ├─→ Include confidence scores
  │
  ├─→ Include validator used
  │
  └─→ Include timestamp
    │
    ▼
Store evidence:
  - rule_result_id
  - ocr_block_id
  - bounding_box
  - confidence
  - validator_name
  - timestamp
```

### Phase 8: Report Generation

```
GET /api/v1/analyses/{id}/report
    │
    ▼
Load analysis + all related data:
  - Product info
  - Images
  - Extracted fields
  - Rule results
  - Evidence
    │
    ▼
Generate PDF using ReportLab:
  │
  ├─→ Header:
  │     - Report title
  │     - Analysis ID
  │     - Date
  │     - User
  │
  ├─→ Product Information:
  │     - Name, category
  │     - Extracted fields
  │
  ├─→ Compliance Summary:
  │     - Overall status
  │     - Pass/Fail/Review counts
  │
  ├─→ Detailed Results:
  │     - Per-rule results
  │     - Evidence for each
  │
  └─→ Footer:
        - Limitations
        - Disclaimers
    │
    ▼
Save to: reports/analysis_{id}.pdf
    │
    ▼
Return: PDF file
```

## Database Relationships

```
User
  │
  └── Analysis (1:N)
        │
        ├── Product (N:1)
        │
        ├── ProductImage (1:N)
        │
        ├── OCRResult (1:1)
        │
        ├── ExtractedField (1:N)
        │
        ├── RuleResult (1:N)
        │     │
        │     └── Evidence (1:N)
        │
        └── Inspection (1:N, optional)
```

## Error Data Flow

```
Validation Error
    │
    ▼
Pydantic ValidationError
    │
    ▼
FastAPI auto-returns 422 with details
    │
    ▼
Client displays field-level errors

Processing Error
    │
    ▼
Service raises exception
    │
    ▼
FastAPI exception handler
    │
    ▼
Returns 500 with error ID
    │
    ▼
Error logged to audit_logs table
```
