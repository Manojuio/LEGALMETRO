# Rule Registry

## Overview

This directory contains the structured legal rule registry for the Packaged Commodities Compliance Scanner.

## Files

| File | Purpose |
|------|---------|
| `rules.json` | Complete rule definitions from Legal Metrology (Packaged Commodities) Rules, 2011 |
| `categories.json` | Product categories and subcategories with applicable rules |
| `exemptions.json` | Legal exemptions from labeling requirements |
| `standard_packages.json` | Standard package quantities per First Schedule |

## Rule Structure

Each rule in `rules.json` contains:

- `id`: Unique identifier (format: `LM-R{number}-{sequence}`)
- `rule_number`: Legal rule number from the Act
- `title`: Short description
- `category`: Rule category (DECLARATIONS, QUANTITY, PRICE, MANUFACTURER, DATES, VISUAL, PHYSICAL, ADMINISTRATIVE)
- `source_reference`: Legal reference
- `requirement`: Full legal requirement text
- `input_fields`: Fields needed for validation
- `validation_type`: How the rule is validated
- `severity`: Impact level (HIGH, MEDIUM, LOW)
- `automation_level`: How it can be automated
- `applicable_to`: Which products it applies to
- `evidence_required`: What evidence is needed
- `limitations`: Known limitations

## Automation Levels

| Level | Description |
|-------|-------------|
| `AUTOMATED` | Fully determinizable from image |
| `AI_ASSISTED` | Image analysis with confidence |
| `HUMAN_REVIEW` | Requires human judgment |
| `PHYSICAL_TEST_REQUIRED` | Requires physical measurement |
| `ADMINISTRATIVE` | Outside image scanner scope |

## Validation Types

| Type | Description |
|------|-------------|
| `FIELD_PRESENT` | Check if field is extracted |
| `UNIT_VALIDATION` | Validate unit of measurement |
| `STANDARD_QUANTITY` | Check against standard quantities |
| `DIMENSION_VALIDATION` | Font size / dimension check |
| `PRICE_VALIDATION` | Price format and presence |
| `DATE_VALIDATION` | Date format and presence |
| `TEXT_LEGIBILITY` | Legibility assessment |
| `PLACEMENT_REVIEW` | Text placement assessment |
| `PHYSICAL_TEST_REQUIRED` | Cannot be done from image |

## Usage

The rule registry is loaded by the applicability engine and compliance engine:

1. Product is classified into a category
2. Applicable rules are determined from category
3. Exemptions are checked
4. Remaining rules are validated by their validators

## Legal Disclaimer

This registry is for prototype demonstration purposes. It does not constitute legal advice. The rules are interpreted from the Legal Metrology (Packaged Commodities) Rules, 2011. For official interpretation, consult the official gazette.
