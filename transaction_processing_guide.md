# Transaction Processing Guide

This document outlines the architecture, rules, and filters used by the spending analysis system.

## Project Structure

```
YearlySpending/
├── spending/                    # Shared library (year-agnostic)
│   ├── models.py                # Transaction dataclass
│   ├── parsers.py               # Chase, Amex, BoA CSV parsers
│   ├── rules.py                 # Categories, tax exclusion, reimbursable tagging
│   ├── filters.py               # Transfer/refund detection, final filtering
│   └── dashboard_template.py    # Interactive HTML/JS dashboard template
├── data/<year>/                 # Raw CSV files per year
├── output/<year>/               # Generated reports per year (or "all" for combined)
├── analyze.py                   # CLI entry point
└── transaction_processing_guide.md
```

### Usage
```bash
python analyze.py --year 2025       # Single year
python analyze.py --year all        # Combined multi-year view
```

## 1. Data Model (`models.py`)

All transactions are normalized to a `Transaction` dataclass:
- **amount**: Positive = Spending (Debit), Negative = Credit/Refund
- **date**: Python `datetime` object
- **source**: `'Chase'`, `'Amex'`, or `'BOA-XXXX'` (account last digits)
- **category**: Starts as `'Uncategorized'`, overridden by rules
- **txn_id**: MD5 hash of `date + description + amount + source`

## 2. Parsers (`parsers.py`)

| Bank | Key Rules |
|:---|:---|
| **Chase** | Skips `Type == 'Payment'`. Inverts amount (Chase exports spending as negative). |
| **Amex** | Skips `AUTOPAY`/`PAYMENT` in description. Amounts parsed as-is. |
| **BoA** | Extracts account digits for source name. Inverts amounts. Excludes `Online Banking transfer`, CC autopay keywords (`CHASE CREDIT CRD`, `AMEX`, etc.). |

`auto_parse(file_path)` auto-detects format from filename.

## 3. Filters (`filters.py`)

### A. Cross-Account Transfer Detection
Matches transactions with **same date** and **opposite amounts** across different BOA accounts. Both sides flagged as `is_internal_transfer` and excluded.

### B. Refund Matching
For **Chase/Amex only**: matches credits with debits of the same amount within a **90-day** window. Both sides flagged as `is_refunded` and excluded.

### C. Tax Exclusion
Keywords excluded: `FRANCHISE TAX`, `IRS`, `USATAXPYMT`, `PTY TAX`, `SANTA CLARA DTAC`, `ALAMEDA COUNTY`.

## 4. Categorization Rules (`rules.py`)

| Category | Keyword / Rule |
|:---|:---|
| **HOA - StJames** | `CITY HEIGHTS AT` + `WEB PMTS`, or `CLICKPAY` + `PROPRTYPAY` |
| **Rental Management Fee** | `JOYHOME PROPERTY MANAGEMENT` |
| **Long Term Insurance** | `TRANSAMERICA INS` (splits into **- Xin** or **- Jiesi** by name) |
| **Mortgage - CrystalSprings** | `WF HOME MTG` + `27056` |
| **Mortgage - StJames** | `WF HOME MTG` + `24997` |
| **Housing - 1407Cervantas** | `ICHA` + `WEB PMTS` |
| **Daycare** | `UC REGENTS BILL PAYMENT` |
| **Nanny** | `MEIHUA` |
| **INIT Wire** | `WIRE TYPE:INTL OUT` |

To add a new rule: edit `CATEGORY_RULES` list in `rules.py`.

## 5. Reimbursable Items

- **Auto-Tag**: `PROLIFIC_HW` in description → marked reimbursable (configurable in `rules.py` via `REIMBURSABLE_KEYWORDS`)
- **Manual Toggle**: Dashboard checkbox per transaction, persisted in browser `localStorage`
- **Filter**: Global "Exclude Reimbursable" toggle in dashboard

## 6. Adding a New Year

1. Create `data/<year>/` directory
2. Drop raw CSV files (Chase, Amex, BoA format)
3. Run `python analyze.py --year <year>`
4. Output appears in `output/<year>/`
