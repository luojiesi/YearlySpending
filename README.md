# Yearly Spending Dashboard

A Python-based tool to analyze spending from bank CSV statements and visualize it in a local interactive dashboard.

## Overview

- **Privacy-Focused**: Everything runs locally. No data leaves your machine.
- **Multi-Year Support**: Analyze multiple years (2024, 2025, ...) and switch between them instantly.
- **Interactive Dashboard**: Filter by month, category, source. Click charts to drill down. Edit categories and tags inline.
- **Override System**: Manual changes (reimbursable, not-spending, category) are saved to `overrides.json` and applied on every regeneration.
- **Local Server**: A dev server auto-saves your dashboard edits to disk. Accessible from LAN devices (phone, tablet).

## Quick Start

### 1. Analyze Data

```bash
python analyze.py --year 2025       # single year
python analyze.py --year all        # all years
```

This reads CSVs from `data/{year}/`, runs the processing pipeline, applies any saved overrides, and generates the dashboard files in `output/`.

### 2. Start the Server

```bash
python server.py                    # serves on all interfaces (LAN accessible), port 18234
python server.py --port 9000        # fixed port
python server.py --bind localhost   # localhost only (no LAN access)
python server.py --stop             # stop a running server
```

The server uses port 18234 by default. The LAN URL is also printed on startup for access from other devices on your network.

### 3. Without the Server

You can also open `output/spending_dashboard.html` directly as a `file://` URL. In this mode, overrides are stored in browser localStorage and an "Export Overrides" button appears for manual export.

## Project Structure

```
YearlySpending/
├── analyze.py                # Main entry point - runs the full pipeline
├── server.py                 # Local dev server with override save API & auto-shutdown
├── convert_2024_data.py      # One-time script to convert 2024 raw data into parser-compatible CSVs
├── data/                     # Input: bank CSV files, organized by year
│   ├── 2024/
│   ├── 2025/
│   └── Raw/                  # Original source files for 2024 conversion
├── output/                   # Generated output
│   ├── spending_dashboard.html   # Interactive dashboard (open this)
│   ├── manifest.js               # Lists available years
│   ├── data_2024.js              # JSONP transaction data per year
│   ├── data_2025.js
│   ├── overrides.json            # Manual overrides (reimbursable, not-spending, categories)
│   ├── 2024/                     # Static reports per year
│   │   ├── spending_report.md
│   │   └── spending_summary.csv
│   └── 2025/
│       ├── spending_report.md
│       └── spending_summary.csv
└── spending/                 # Python package
    ├── __init__.py
    ├── models.py             # Transaction dataclass
    ├── parsers.py            # Bank CSV parsers (Chase, Amex, BOA)
    ├── rules.py              # Category rules, tax keywords, reimbursable keywords
    ├── filters.py            # Internal transfer & refund detection
    └── dashboard_template.py # HTML/JS/CSS dashboard generation
```

## Data Pipeline

`analyze.py --year {year}` runs these steps for each year:

1. **Parse** - `parsers.py` scans `data/{year}/*.csv`, auto-detects bank format (Chase, Amex, BOA), and standardizes each row into a `Transaction` object.
2. **Filter** - `filters.py` detects and removes:
   - Cross-account BOA internal transfers (matching opposite amounts on same date)
   - Credit card refunds (matching credit to original debit within 90 days)
   - Non-spending items (BOA deposits, CC autopay, etc.)
3. **Categorize** - `rules.py` applies ordered category rules (first match wins). Includes mortgage, HOA, daycare, insurance, property tax, utilities, etc.
4. **Generate IDs** - Stable MD5-based `TxnID` per transaction (used to track overrides). An index disambiguates otherwise-identical transactions.
5. **Tag** - `rules.py` auto-tags reimbursable transactions (keyword match) and not-spending transactions (income/estimated tax payments).
6. **Apply Overrides** - Loads `output/overrides.json` and applies manual overrides for reimbursable, not-spending, and category fields (by TxnID).
7. **Output** - Generates:
   - `data_{year}.js` — JSONP file (`window.spendingData_{year} = [...]`)
   - `manifest.js` — list of available years
   - `spending_dashboard.html` — full interactive dashboard
   - `{year}/spending_report.md` and `spending_summary.csv` — static reports

## Server Details

### Binding & LAN Access

By default the server binds to `0.0.0.0` (all network interfaces), making the dashboard accessible from any device on your local network (phone, tablet, etc.). The LAN URL is printed on startup.

Use `--bind localhost` to restrict access to only the local machine.

Windows Firewall may prompt you to allow the connection the first time.

### Auto-Shutdown

The server uses a heartbeat system to automatically shut down when no longer needed:

| Scenario | Behavior |
|---|---|
| No page opened | Server shuts down after **120 seconds** (initial grace period) |
| Page open, then closed | Server shuts down after **60 seconds** without a heartbeat |
| Computer sleeps and wakes | Server detects the sleep gap and gives a **15-second grace period** for the page to reconnect before applying the normal timeout |

The dashboard page sends a heartbeat every 30 seconds. It also sends an immediate heartbeat on `visibilitychange` (tab becomes visible) and `focus` (window gains focus), which handles the wake-from-sleep case.

### PID File

The server writes its PID to `.server.pid` in the project root. This enables `python server.py --stop` to find and terminate a running server.

### Server API

| Endpoint | Method | Description |
|---|---|---|
| `GET /api/overrides` | GET | Returns current `overrides.json` content |
| `POST /api/overrides` | POST | Saves JSON body to `overrides.json` on disk |
| `GET /api/heartbeat` | GET | Records a heartbeat, resets the auto-shutdown timer |
| `GET /*` | GET | Serves static files from `output/` |

## Overrides System

The dashboard lets you make manual corrections that override the auto-tagging rules:

| Override | What it does | Column in dashboard |
|---|---|---|
| **Reimbursable** | Marks a transaction as reimbursable (excluded from totals by default) | Checkbox in "Reimb." column |
| **Not Spending** | Marks a transaction as not real spending, e.g. tax payments | Checkbox in "Not Spending" column |
| **Category** | Reassigns a transaction to a different or new category | Dropdown in "Category" column |

### How overrides flow

```
Browser toggle/change
       │
       ├──► localStorage (fallback for file:// mode)
       │
       └──► POST /api/overrides ──► output/overrides.json (on disk)
                                          │
                                          ▼
                           python analyze.py --year all
                                          │
                                          ▼
                              data_{year}.js (overrides baked in)
```

- **With server** (`python server.py`): Every checkbox toggle or category change is auto-saved to `output/overrides.json` via the API.
- **Without server** (`file://`): Overrides live in browser localStorage. Use the "Export Overrides" button to download `overrides.json`, then place it in `output/`.
- **On regeneration** (`python analyze.py`): Overrides are loaded from `output/overrides.json` and applied after the auto-tagging step, so manual corrections survive re-runs.

### overrides.json format

```json
{
  "reimbursable": {
    "txn_id_hash": true
  },
  "notSpending": {
    "txn_id_hash": true
  },
  "categories": {
    "txn_id_hash": "New Category Name"
  }
}
```

## Dashboard Features

- **Year tabs** — switch between years; filter state is remembered per year
- **Filter dropdowns** — Month, Category, Source (multi-select)
- **Exclude dropdown** — toggle exclusion of Reimbursable and Not Spending transactions
- **Search** — free-text search across description, category, and source
- **Charts** — monthly bar chart, category pie chart, source pie chart (click to filter); clean dollar formatting on axes and hover
- **Table stats** — live summary next to the table header showing row count, sum, and average for the current filter
- **Sortable table** — click column headers to sort (supports multi-column sort)
- **Inline editing** — change category via dropdown, toggle reimbursable/not-spending checkboxes
- **Reset Filters** — restores default view (excludes reimbursable + not-spending)
- **Column resizing** — drag column borders to resize

## Source Modules

### `spending/models.py` — Transaction

The core data structure. A `@dataclass` with fields:

| Field | Type | Description |
|---|---|---|
| `date` | `datetime` | Transaction date |
| `description` | `str` | Raw description from bank |
| `amount` | `float` | Positive = spending, negative = credit |
| `category` | `str` | Auto or manually assigned category |
| `source` | `str` | Bank identifier (e.g. `Chase`, `BOA-4364`, `Amex`) |
| `source_file` | `str` | Original CSV filename |
| `is_spending` | `bool` | False for deposits, autopay, etc. |
| `is_internal_transfer` | `bool` | Matched as cross-account transfer |
| `is_refunded` | `bool` | Matched with a refund credit |
| `is_reimbursable` | `bool` | Tagged as reimbursable |
| `is_not_spending` | `bool` | Tagged as not real spending (tax payments) |
| `txn_id` | `str` | Stable MD5 hash for override tracking |

Properties: `month` (YYYY-MM string), `year` (int).

### `spending/parsers.py` — Bank CSV Parsers

Three parsers, auto-selected by filename pattern:

| Parser | Filename match | Format notes |
|---|---|---|
| `parse_chase` | `chase` in filename | Negative amounts = spending. Skips `Payment` type rows. |
| `parse_amex` | `amex` or `activity` in filename | Positive amounts = spending. Skips `AUTOPAY`/`PAYMENT` descriptions. |
| `parse_boa` | `boa` or `stmt` in filename | CSV has a header block before the data rows. Negative CSV values = debits = spending. Skips CC autopay, online transfers. |

`auto_parse(file_path)` selects the correct parser based on the filename.

### `spending/rules.py` — Business Rules

**Category rules** (`CATEGORY_RULES`): Ordered list of `(match_fn, category)` tuples. The match function receives the uppercased description. First match wins. Special handling for Transamerica insurance (dynamic category based on `INDN:` field).

**Tax keywords** (`TAX_KEYWORDS`): `FRANCHISE TAX`, `IRS DES:`, `USATAXPYMT`. Transactions matching these are tagged `is_not_spending = True`.

**Reimbursable keywords** (`REIMBURSABLE_KEYWORDS`): `PROLIFIC_HW`, `ALAMEDA COUNTY WATER`. Matching transactions are tagged `is_reimbursable = True`.

### `spending/filters.py` — Filtering Logic

| Filter | Logic |
|---|---|
| `detect_internal_transfers` | Groups BOA transactions by source file, then matches pairs across files with same date and inverse amounts. |
| `detect_refunds` | For Chase/Amex, matches credit amounts to debit amounts within the same source, same amount, within 90 days. Closest date match wins. |
| `apply_final_filters` | Removes internal transfers, refunds, and non-spending items. Tax transactions are kept (tagged, not removed). |

## 2024 Data Conversion

`convert_2024_data.py` is a one-time script that converts raw 2024 data (exported spreadsheets and BOA PDF statements) into the standard CSV format expected by the parsers.

### Sources

| Source file | Contents |
|---|---|
| `all_expenses_jan-june2024.xlsx - all_credit_cards.csv` | Jan-June 2024 credit card transactions (Chase + Amex) |
| `all_expenses_20240701_20250607.xlsx - all.csv` | Jul 2024 - Jun 2025 all accounts |
| `BOA_4364stmt.csv` | Jan-June 2024 BOA 4364 checking |
| `BOA_4364_eStmt_*.pdf` | BOA 4364 monthly PDF statements |
| `BOA_4377_eStmt_*.pdf` | BOA 4377 monthly PDF statements |

### Outputs (in `data/2024/`)

`Chase_9300.csv`, `Chase_7179.csv`, `Amex.csv`, `BOA_4364.csv`, `BOA_4377.csv`

The script cross-verifies BOA 4377 data between PDF and CSV sources for the overlapping Jul-Dec period. PDF data is used as the primary source (covers the full year).

Requires `pdfplumber` for PDF extraction: `pip install pdfplumber`.

## Adding New Data

1. Download CSV statements from your bank (Chase, Amex, or Bank of America).
2. Place them in `data/{year}/` (filename must contain `chase`, `amex`/`activity`, or `boa`/`stmt` for auto-detection).
3. Run `python analyze.py --year {year}`.
4. Refresh the dashboard.

## Setting up Business Rules (First Time Setup)

Before running the tool for the first time, you need to set up your personal categorization rules:

1. Copy `spending/rules.template.py` to `spending/rules.py`:
   ```bash
   cp spending/rules.template.py spending/rules.py
   ```
2. Open `spending/rules.py` and customize `TAX_KEYWORDS`, `CATEGORY_RULES`, and `REIMBURSABLE_KEYWORDS` to match your own bank statements. Your custom `rules.py` is ignored by git to keep your personal info private.

## Adding Category Rules

Edit `spending/rules.py` and add entries to `CATEGORY_RULES`:
```python
CATEGORY_RULES = [
    (lambda d: 'SOME MERCHANT' in d, 'Category Name'),
    # ... existing rules
]
```

Rules are checked in order; first match wins. The description is uppercased before matching.

## Adding Reimbursable or Tax Keywords

Edit `spending/rules.py`:

```python
REIMBURSABLE_KEYWORDS = ['PROLIFIC_HW', 'ALAMEDA COUNTY WATER']
TAX_KEYWORDS = ['FRANCHISE TAX', 'IRS DES:', 'USATAXPYMT']
```

Reimbursable transactions are included in data but excluded from totals by default. Tax-keyword transactions are tagged as "Not Spending".

## Dependencies

- **Python 3.10+** (uses `X | Y` union type syntax)
- **pdfplumber** — only needed for `convert_2024_data.py` (BOA PDF extraction)
- No other external dependencies. The dashboard is pure HTML/JS/CSS with no build step.
