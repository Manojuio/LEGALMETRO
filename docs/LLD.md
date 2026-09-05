# Low Level Design

## Database Schema

### users

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PRIMARY KEY |
| email | VARCHAR(255) | UNIQUE, NOT NULL |
| hashed_password | VARCHAR(255) | NOT NULL |
| full_name | VARCHAR(255) | NOT NULL |
| role | ENUM | NOT NULL (ADMIN, LMO, MANUFACTURER, RETAILER, CONSUMER) |
| is_active | BOOLEAN | DEFAULT TRUE |
| created_at | TIMESTAMP | DEFAULT NOW() |
| updated_at | TIMESTAMP | DEFAULT NOW() |

### products

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PRIMARY KEY |
| name | VARCHAR(255) | NOT NULL |
| category | VARCHAR(100) | NOT NULL |
| subcategory | VARCHAR(100) | |
| brand | VARCHAR(255) | |
| description | TEXT | |
| created_by | UUID | FOREIGN KEY → users.id |
| created_at | TIMESTAMP | DEFAULT NOW() |
| updated_at | TIMESTAMP | DEFAULT NOW() |

### analyses

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PRIMARY KEY |
| user_id | UUID | FOREIGN KEY → users.id |
| product_id | UUID | FOREIGN KEY → products.id, NULLABLE |
| status | ENUM | DEFAULT PENDING |
| overall_status | ENUM | NULLABLE |
| category | VARCHAR(100) | |
| subcategory | VARCHAR(100) | |
| summary_json | JSONB | |
| created_at | TIMESTAMP | DEFAULT NOW() |
| updated_at | TIMESTAMP | DEFAULT NOW() |

### product_images

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PRIMARY KEY |
| analysis_id | UUID | FOREIGN KEY → analyses.id |
| filename | VARCHAR(255) | NOT NULL |
| file_path | VARCHAR(500) | NOT NULL |
| file_size | INTEGER | NOT NULL |
| mime_type | VARCHAR(50) | NOT NULL |
| image_position | ENUM | NOT NULL (FRONT, BACK, SIDE, OTHER) |
| width | INTEGER | |
| height | INTEGER | |
| created_at | TIMESTAMP | DEFAULT NOW() |

### ocr_results

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PRIMARY KEY |
| analysis_id | UUID | FOREIGN KEY → analyses.id, UNIQUE |
| image_id | UUID | FOREIGN KEY → product_images.id |
| raw_text | TEXT | |
| text_blocks | JSONB | NOT NULL |
| confidence_score | FLOAT | |
| processing_time_ms | INTEGER | |
| ocr_engine | VARCHAR(50) | DEFAULT 'easyocr' |
| created_at | TIMESTAMP | DEFAULT NOW() |

### extracted_fields

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PRIMARY KEY |
| analysis_id | UUID | FOREIGN KEY → analyses.id |
| field_name | VARCHAR(100) | NOT NULL |
| field_value | TEXT | |
| field_value_numeric | FLOAT | |
| confidence | FLOAT | |
| source_text | TEXT | |
| source_image_id | UUID | FOREIGN KEY → product_images.id |
| extraction_method | VARCHAR(50) | |
| created_at | TIMESTAMP | DEFAULT NOW() |

### rules

| Column | Type | Constraints |
|--------|------|-------------|
| id | VARCHAR(20) | PRIMARY KEY (e.g., LM-R6-001) |
| rule_number | VARCHAR(10) | NOT NULL |
| title | VARCHAR(255) | NOT NULL |
| category | VARCHAR(100) | NOT NULL |
| source_reference | VARCHAR(100) | |
| requirement | TEXT | NOT NULL |
| input_fields | JSONB | |
| validation_type | VARCHAR(50) | NOT NULL |
| severity | VARCHAR(20) | NOT NULL |
| automation_level | VARCHAR(50) | NOT NULL |
| applicable_to | JSONB | |
| package_types | JSONB | |
| evidence_required | JSONB | |
| limitations | TEXT | |
| is_active | BOOLEAN | DEFAULT TRUE |
| created_at | TIMESTAMP | DEFAULT NOW() |
| updated_at | TIMESTAMP | DEFAULT NOW() |

### rule_results

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PRIMARY KEY |
| analysis_id | UUID | FOREIGN KEY → analyses.id |
| rule_id | VARCHAR(20) | FOREIGN KEY → rules.id |
| status | ENUM | NOT NULL (PASS, FAIL, REVIEW, NOT_APPLICABLE) |
| reason | TEXT | |
| confidence | FLOAT | |
| validator_name | VARCHAR(100) | |
| processing_time_ms | INTEGER | |
| created_at | TIMESTAMP | DEFAULT NOW() |

### rule_result_evidence

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PRIMARY KEY |
| rule_result_id | UUID | FOREIGN KEY → rule_results.id |
| evidence_type | VARCHAR(50) | NOT NULL |
| ocr_text | TEXT | |
| bounding_box | JSONB | |
| confidence | FLOAT | |
| source_image_id | UUID | FOREIGN KEY → product_images.id |
| created_at | TIMESTAMP | DEFAULT NOW() |

### inspections

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PRIMARY KEY |
| analysis_id | UUID | FOREIGN KEY → analyses.id |
| user_id | UUID | FOREIGN KEY → users.id |
| location | VARCHAR(500) | |
| status | ENUM | DEFAULT PENDING |
| observations | TEXT | |
| notes | TEXT | |
| created_at | TIMESTAMP | DEFAULT NOW() |
| updated_at | TIMESTAMP | DEFAULT NOW() |

### reports

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PRIMARY KEY |
| analysis_id | UUID | FOREIGN KEY → analyses.id |
| file_path | VARCHAR(500) | NOT NULL |
| file_size | INTEGER | |
| generated_at | TIMESTAMP | DEFAULT NOW() |

### audit_logs

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PRIMARY KEY |
| user_id | UUID | FOREIGN KEY → users.id |
| action | VARCHAR(100) | NOT NULL |
| entity_type | VARCHAR(50) | |
| entity_id | UUID | |
| details | JSONB | |
| ip_address | VARCHAR(45) | |
| created_at | TIMESTAMP | DEFAULT NOW() |

## Indexes

- users: email (unique)
- analyses: user_id, status
- product_images: analysis_id
- ocr_results: analysis_id
- extracted_fields: analysis_id
- rule_results: analysis_id, rule_id
- rule_result_evidence: rule_result_id
- inspections: user_id, analysis_id
- reports: analysis_id
- audit_logs: user_id, action, created_at

## Enums

```
user_role: ADMIN, LMO, MANUFACTURER, RETAILER, CONSUMER
analysis_status: PENDING, PROCESSING, COMPLETED, FAILED
analysis_overall_status: PASS, FAIL, REVIEW
image_position: FRONT, BACK, SIDE, OTHER
rule_status: PASS, FAIL, REVIEW, NOT_APPLICABLE
inspection_status: PENDING, IN_PROGRESS, COMPLETED, CANCELLED
```

## Relationships

```
User 1──N Analysis
Product 1──N Analysis
Analysis 1──1 ProductImage (multiple)
Analysis 1──1 OCRResult (multiple, per image)
Analysis 1──N ExtractedField
Analysis 1──N RuleResult
RuleResult 1──N RuleResultEvidence
Analysis 1──N Inspection
Analysis 1──N Report
User 1──N AuditLog
```
