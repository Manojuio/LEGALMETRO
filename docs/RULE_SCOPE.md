# Rule Scope

## Legal Source

**Legal Metrology (Packaged Commodities) Rules, 2011**
Under the Legal Metrology Act, 2009

## Rules In Scope

### Automatically Verifiable from Images

These rules can be validated using OCR-extracted text and image analysis:

| Rule | Title | Validation Type | Confidence |
|------|-------|----------------|------------|
| 3 | Package to bear prescribed information | Text present/absent check | High |
| 4 | Name, address of manufacturer/packer/importer | Text extraction + presence | High |
| 5 | Name of commodity | Text extraction + presence | High |
| 6 | Mandatory declarations | Field presence validation | High |
| 7 | Height of numerals (MRP, net quantity) | Font size estimation via CV | Medium |
| 8 | Declarations to be on principal display panel | Placement review via CV | Medium |
| 9 | Legibility of declarations | Contrast/legibility via CV | Medium |
| 10 | Manufacturer/packer/importer details | Text extraction + presence | High |
| 11 | Consumer care contact | Text extraction + presence | High |
| 12 | Net quantity in SI units | Unit validation | High |
| 13 | Standard quantities for package sizes | Database lookup | High |
| 14 | Unit pricing | Price format validation | High |
| 15 | Date marking format | Date format validation | High |
| 16 | Country of origin (for imports) | Text extraction | High |
| 17 | Pre-packaged commodity definition compliance | Category-based check | High |

### AI/CV-Assisted Checks

These rules benefit from computer vision but may need human review:

| Rule | Title | Validation Type | Confidence |
|------|-------|----------------|------------|
| 7 | Font size estimation | Image analysis + estimation | Medium |
| 8 | Placement on principal display | Image analysis + positioning | Medium |
| 9 | Legibility and contrast | Image analysis + contrast measurement | Medium |

### Checks Requiring Human Review

These rules cannot be reliably determined from images alone:

| Rule | Title | Why Human Review |
|------|-------|-----------------|
| 22 | Complaints handling procedure details | May require document verification |
| 23 | Specific label language requirements | Regional language verification needed |
| 24 | Import-specific markings | May need supporting documents |

### Checks Requiring Physical Measurement

These rules involve physical inspection that cannot be done from images:

| Rule | Title | Physical Requirement |
|------|-------|---------------------|
| 19 | Actual quantity verification | Weighing/measurement required |
| 20 | Maximum permissible errors | Physical testing required |
| 21 | Sampling and testing procedures | Laboratory testing required |

**These are explicitly NOT implemented as image-based rules.**

### Administrative Checks

These are outside the image scanner:

| Rule | Title | Administrative Requirement |
|------|-------|--------------------------|
| 1 | Short title and commencement | Legal document check |
| 2 | Definitions and interpretations | Legal document check |
| 18 | Exemptions from labeling | Exemption certificate check |
| 25 | Penalties and enforcement | Legal process check |
| 26 | Power to make rules | Legal authority check |

## Rule Categories

### DECLARATIONS
Rules about what information must be present on the label.

### QUANTITY
Rules about net quantity, units, and standard packages.

### PRICE
Rules about MRP, pricing, and unit pricing.

### MANUFACTURER
Rules about manufacturer/packer/importer identification.

### DATES
Rules about date marking and shelf life.

### VISUAL
Rules about font size, placement, legibility, and contrast.

### PHYSICAL
Rules requiring physical measurement or testing.

### ADMINISTRATIVE
Rules that are administrative or legal in nature.

## Automation Levels

| Level | Description | Example |
|-------|-------------|---------|
| AUTOMATED | Fully determinizable from image | Field presence, unit validation |
| AI_ASSISTED | Image analysis with confidence threshold | Font size, contrast |
| HUMAN_REVIEW | Requires human judgment | Complex placements, ambiguities |
| PHYSICAL_TEST_REQUIRED | Requires physical measurement | Quantity verification |
| ADMINISTRATIVE | Outside image scanner scope | Legal document checks |

## Limitations

1. **OCR accuracy** depends on image quality, packaging design, and text clarity
2. **Physical quantity** cannot be verified from images
3. **Font size estimation** from photos is approximate, not precise measurement
4. **Multi-language labels** may have mixed OCR accuracy
5. **Curved or reflective packaging** degrades OCR quality
6. **Small text** may fall below OCR confidence thresholds
7. **Handwritten text** is not reliably OCR'd
8. **This system does not certify products** — it provides compliance guidance
