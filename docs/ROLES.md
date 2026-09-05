# Roles

## Role Definitions

### ADMIN

**Purpose:** System administrator with full access.

**Responsibilities:**
- Manage users (create, update, deactivate)
- Manage compliance rules
- Manage product categories
- Manage standard package rules
- View all analyses across the system
- View system statistics
- Configure system settings

**Access Level:** Full system access.

### LMO (Legal Metrology Officer)

**Purpose:** Enforcement officer performing product inspections.

**Responsibilities:**
- Upload product images during field inspection
- Perform compliance analysis
- View detailed compliance results
- Create inspection records
- Generate compliance reports
- View inspection history
- Record physical findings

**Access Level:** Analysis, inspection, and reporting functions.

### MANUFACTURER

**Purpose:** Product manufacturer performing pre-launch compliance checks.

**Responsibilities:**
- Create and manage products
- Upload packaging design images
- Run pre-launch compliance checks
- Save analysis results
- View analysis history
- Download compliance reports

**Access Level:** Product management and analysis for own products.

### RETAILER

**Purpose:** Retailer verifying product compliance at point of sale.

**Responsibilities:**
- Scan product images
- Check MRP and declarations
- View compliance reports
- View scan history

**Access Level:** Scanning and analysis viewing.

### CONSUMER

**Purpose:** End consumer checking product compliance.

**Responsibilities:**
- Scan product images
- View simplified compliance result
- View detected MRP and quantity
- View warnings

**Access Level:** Basic scanning with limited results.

### GUEST (Optional)

**Purpose:** Unauthenticated public scanning.

**Responsibilities:**
- Scan product images
- View limited compliance result

**Access Level:** Minimal, no data persistence.

## Role Access Matrix

### Endpoint Access

| Endpoint | ADMIN | LMO | MANUFACTURER | RETAILER | CONSUMER |
|----------|-------|-----|--------------|----------|----------|
| POST /auth/register | - | - | - | - | - |
| POST /auth/login | Yes | Yes | Yes | Yes | Yes |
| GET /auth/me | Yes | Yes | Yes | Yes | Yes |
| GET /users/me | Yes | Yes | Yes | Yes | Yes |
| PATCH /users/me | Yes | Yes | Yes | Yes | Yes |
| GET /users | Yes | - | - | - | - |
| PATCH /users/{id} | Yes | - | - | - | - |
| POST /products | Yes | - | Yes | - | - |
| GET /products | Yes | Yes | Yes | Yes | - |
| GET /products/{id} | Yes | Yes | Yes | Yes | - |
| PATCH /products/{id} | Yes | Limited | Yes | - | - |
| DELETE /products/{id} | Yes | - | Yes | - | - |
| POST /analyses | Yes | Yes | Yes | Yes | Yes |
| GET /analyses | Yes | Yes | Yes | Yes | Yes |
| GET /analyses/{id} | Yes | Yes | Yes | Yes | Yes |
| DELETE /analyses/{id} | Yes | Yes | Yes | Yes | Yes |
| POST /analyses/{id}/images | Yes | Yes | Yes | Yes | Yes |
| GET /analyses/{id}/images | Yes | Yes | Yes | Yes | Yes |
| DELETE /analyses/{id}/images/{image_id} | Yes | Yes | Yes | Yes | Yes |
| POST /analyses/{id}/ocr | Yes | Yes | Yes | Yes | Yes |
| GET /analyses/{id}/ocr | Yes | Yes | Yes | Yes | Yes |
| POST /analyses/{id}/extract | Yes | Yes | Yes | Yes | Yes |
| GET /analyses/{id}/fields | Yes | Yes | Yes | Yes | Yes |
| POST /analyses/{id}/classify | Yes | Yes | Yes | Yes | Yes |
| POST /analyses/{id}/applicability | Yes | Yes | Yes | Yes | Yes |
| POST /analyses/{id}/validate | Yes | Yes | Yes | Yes | Yes |
| POST /analyses/{id}/run | Yes | Yes | Yes | Yes | Yes |
| GET /analyses/{id}/results | Yes | Yes | Yes | Yes | Yes |
| GET /rules | Yes | Yes | Yes | Yes | Yes |
| GET /rules/{id} | Yes | Yes | Yes | Yes | Yes |
| POST /rules | Yes | - | - | - | - |
| PATCH /rules/{id} | Yes | - | - | - | - |
| POST /inspections | Yes | Yes | - | - | - |
| GET /inspections | Yes | Yes | - | - | - |
| GET /inspections/{id} | Yes | Yes | - | - | - |
| PATCH /inspections/{id} | Yes | Yes | - | - | - |
| GET /analyses/{id}/report | Yes | Yes | Yes | Yes | Limited |
| GET /health | Yes | Yes | Yes | Yes | Yes |
| GET /api/v1/version | Yes | Yes | Yes | Yes | Yes |

### Key Principles

1. **Role-based access controls operations, not the compliance engine.**
2. The rule engine does not care whether the request came from an LMO or manufacturer.
3. Access control is implemented via FastAPI dependencies, not scattered if-else checks.
4. "Limited" access means restricted response fields or simplified view.
