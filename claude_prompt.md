I am building a local Yearly Spending Dashboard in Python. I recently refactored it to use a "JSONP"-style architecture where the HTML dashboard is a static shell that loads data dynamically from `data_{year}.js` files. This allows the dashboard to verify local file access (file://) without CORS issues, while remaining a Single Page Application.

Please review my implementation for:
1.  **Architecture Soundness**: Is the JSONP approach robust for this use case? Are there edge cases I missed?
2.  **Code Quality**: Python script organization and JavaScript logic.
3.  **UI/UX**: The dynamic loading mechanism and filter logic.
4.  **Extensibility**: How easy is it to add new features?

Here are the key files:

## 1. README.md (Project Overview)

```markdown
# Yearly Spending Dashboard

A Python-based tool to analyze spending from CSV/PDF statements and visualize it in a local interactive dashboard.

## Overview

-   **Privacy-Focused**: Everything runs locally. No data leaves your machine.
-   **Static Dashboard**: Generates a standalone HTML file + JSONP data files. Works without a web server.
-   **Multi-Year Support**: Analyze multiple years (e.g., 2024, 2025) and switch between them instantly.
-   **Extensible**: Easy to add new parsers for different banks.

## Quick Start

### 1. Project Structure
project/
├── data/               # Input data (CSV, PDF statement extracts)
│   ├── 2024/
│   ├── 2025/
├── output/             # Generated Dashboard & Reports
│   ├── spending_dashboard.html  <-- OPEN THIS
│   ├── manifest.js
│   ├── data_2024.js
│   ├── data_2025.js
│   └── 2024/           # Static Reports
│       ├── spending_report.md
│       └── spending_summary.csv
├── spending/           # Python Source Code
│   ├── models.py
│   ├── parsers.py
│   ├── rules.py
│   ├── ...
├── analyze.py          # Main Script

### 2. Running Analysis
python analyze.py --year 2025       # Single year
python analyze.py --year all        # Analyze all years
```

## 2. analyze.py (Main Entry Point)

```python
"""
Main entry point for spending analysis.
Usage:
    python analyze.py --year 2025       # Analyze single year, update dashboard data
    python analyze.py --year all        # Analyze all years, update all dashboard data
"""
import argparse
import csv
import glob
import os
import re
from collections import defaultdict
from typing import List

from spending.models import Transaction
from spending.parsers import auto_parse
from spending.rules import apply_categories, generate_ids, tag_reimbursable
from spending.filters import detect_internal_transfers, detect_refunds, apply_final_filters
from spending.dashboard_template import generate_data_js, generate_manifest_js, generate_dashboard_shell

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')
OUTPUT_DIR = os.path.join(BASE_DIR, 'output')


def get_available_years() -> List[str]:
    """Return list of years available in the data directory."""
    dirs = glob.glob(os.path.join(DATA_DIR, '*'))
    years = [os.path.basename(d) for d in dirs if os.path.isdir(d) and os.path.basename(d).isdigit()]
    return sorted(years)


def load_year_data(year: str) -> List[Transaction]:
    """Load and process data for a specific year, returning final transactions."""
    data_dir = os.path.join(DATA_DIR, year)
    if not os.path.isdir(data_dir):
        print(f"Error: Data directory not found for {year}")
        return []

    # 1. Load files
    files = glob.glob(os.path.join(data_dir, '*.[cC][sS][vV]'))
    all_txns = []
    print(f"[{year}] Found {len(files)} files.")
    
    for f in files:
        fname = os.path.basename(f)
        if fname.startswith('spending_'): continue
        
        txns = auto_parse(f)
        if txns:
            all_txns.extend(txns)

    print(f"[{year}] Total parsed: {len(all_txns)}")

    # 2. Filter by year (sanity check)
    target_year = int(year)
    all_txns = [t for t in all_txns if t.year == target_year]
    
    # 3. Processing Pipeline
    detect_internal_transfers(all_txns)
    detect_refunds(all_txns)
    final_txns = apply_final_filters(all_txns)
    apply_categories(final_txns)
    generate_ids(final_txns)
    tag_reimbursable(final_txns)

    print(f"[{year}] Final count: {len(final_txns)}")
    return final_txns


def generate_static_reports(transactions: List[Transaction], output_subdir: str, title: str) -> None:
    """Generate Markdown report and CSV summary."""
    os.makedirs(output_subdir, exist_ok=True)
    # ... (Simplified: generates markdown and CSV) ...
    pass 


def main():
    parser = argparse.ArgumentParser(description='Analyze spending data')
    parser.add_argument('--year', required=True, help='Year to analyze (e.g. 2025) or "all"')
    args = parser.parse_args()

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    years_to_process = []
    if args.year == 'all':
        years_to_process = get_available_years()
    else:
        years_to_process = [args.year]

    if not years_to_process:
        print("No years found to process.")
        return

    all_years_combined = []

    for year in years_to_process:
        print(f"\\n--- Processing {year} ---")
        txns = load_year_data(year)
        if not txns:
            continue
            
        # 1. Generate Data JS for Dashboard (Root Output)
        generate_data_js(txns, year, OUTPUT_DIR)
        
        # 2. Generate Static Reports (Subdir)
        subdir = os.path.join(OUTPUT_DIR, year)
        generate_static_reports(txns, subdir, f"{year} Spending Summary")
        
        all_years_combined.extend(txns)

    # 3. Handle 'all' aggregate report
    if args.year == 'all' and all_years_combined:
        subdir = os.path.join(OUTPUT_DIR, 'all')
        generate_static_reports(all_years_combined, subdir, "All Years Spending Summary")

    # 4. Update Manifest and Dashboard Shell
    search_path = os.path.join(OUTPUT_DIR, 'data_*.js')
    found_files = glob.glob(search_path)
    available_years = []
    for f in found_files:
        match = re.search(r'data_(\d+)\\.js', os.path.basename(f))
        if match:
            available_years.append(match.group(1))
    
    available_years.sort()
    
    print("\\n--- Updating Dashboard ---")
    generate_manifest_js(available_years, OUTPUT_DIR)
    generate_dashboard_shell(OUTPUT_DIR)


if __name__ == "__main__":
    main()
```

## 3. spending/dashboard_template.py (Generator & Shell)

```python
"""
Dashboard HTML template — generates a static shell and JSONP data files.
"""
import json
import os
from .models import Transaction

def generate_data_js(transactions: list[Transaction], year: str, output_dir: str) -> None:
    """Generate a JSONP data file for a specific year."""
    js_data = [t.to_js_dict() for t in transactions]
    content = f"window.spendingData_{year} = {json.dumps(js_data)};"
    path = os.path.join(output_dir, f'data_{year}.js')
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)

def generate_manifest_js(years: list[str], output_dir: str) -> None:
    """Generate the manifest file listing available years."""
    content = f"window.availableYears = {json.dumps(sorted(years))};"
    path = os.path.join(output_dir, 'manifest.js')
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)

def generate_dashboard_shell(output_dir: str, title: str = "Spending Dashboard") -> None:
    """Generate the static HTML shell that loads data dynamically."""
    html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>{title}</title>
    <!-- CSS Styles... -->
    <style>
        .year-tab {{ padding: 8px 16px; cursor: pointer; }}
        .year-tab.active {{ background: #007bff; color: white; }}
        #loading-overlay {{ display: none; ... }}
    </style>
</head>
<body>
    <div id="loading-overlay">Loading data...</div>
    <div class="header">
        <h1>{title}</h1>
        <div id="year-tabs" class="year-tabs"></div>
    </div>
    
    <!-- Filter Controls... -->
    <div class="controls">
        <button onclick="resetFilters()">Reset Filters</button>
        <!-- Dropdowns for Month, Category, Source -->
    </div>

    <!-- Charts and Table... -->

    <!-- Scripts -->
    <script src="manifest.js"></script>
    <script>
        let currentYear = '';
        let rawData = [];
        let currentData = [];
        let activeFilters = {{}};
        
        document.addEventListener('DOMContentLoaded', () => {{
            initYearTabs();
        }});

        function initYearTabs() {{
            const years = window.availableYears || [];
            years.sort().reverse();
            years.forEach(year => {{
                const tab = document.createElement('div');
                tab.className = 'year-tab';
                tab.innerText = year;
                tab.onclick = () => loadYear(year);
                tab.id = 'tab-' + year;
                document.getElementById('year-tabs').appendChild(tab);
            }});
            
            const savedYear = localStorage.getItem('spending_dashboard_last_year');
            loadYear(savedYear && years.includes(savedYear) ? savedYear : years[0]);
        }}

        function loadYear(year) {{
            if (currentYear === year) return;
            document.getElementById('loading-overlay').style.display = 'flex';
            
            // UI Update
            document.querySelectorAll('.year-tab').forEach(t => t.classList.remove('active'));
            document.getElementById('tab-' + year).classList.add('active');
            
            currentYear = year;
            localStorage.setItem('spending_dashboard_last_year', year);

            // Check cache
            const varName = 'spendingData_' + year;
            if (window[varName]) {{
                setRawData(window[varName]);
                return;
            }}

            // Inject JSONP Script
            const script = document.createElement('script');
            script.src = 'data_' + year + '.js';
            script.onload = () => {{
                if (window[varName]) setRawData(window[varName]);
                else alert('Error loading ' + year);
            }};
            document.body.appendChild(script);
        }}

        function setRawData(data) {{
            rawData = data;
            // Apply Manual Reimbursable state from LocalStorage
            // ...
            resetFilters(true); // Reset filters on year switch
            document.getElementById('loading-overlay').style.display = 'none';
        }}
        
        // ... Standard filtering and rendering logic ...
    </script>
</body>
</html>
    """
    path = os.path.join(output_dir, 'spending_dashboard.html')
    with open(path, 'w', encoding='utf-8') as f:
        f.write(html_content)
```

## 4. spending/models.py (Data Model)

```python
"""
Transaction data model.
"""
from dataclasses import dataclass
from datetime import datetime
import hashlib

@dataclass
class Transaction:
    date: datetime
    description: str
    amount: float
    category: str = 'Uncategorized'
    source: str = ''
    # ... other fields ...
    txn_id: str = ''

    def to_js_dict(self) -> dict:
        """Convert to a dict suitable for the dashboard JSON."""
        return {
            'Date': self.date.strftime('%Y-%m-%d'),
            'Description': self.description,
            'Category': self.category,
            'Amount': round(self.amount, 2),
            'Source': self.source,
            'Month': self.month,
            'Year': self.year,
            'TxnID': self.txn_id,
            'IsReimbursable': self.is_reimbursable,
        }
```
