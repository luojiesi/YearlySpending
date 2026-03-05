"""
Main entry point for spending analysis.
Usage:
    python analyze.py --year 2025       # Analyze single year, update dashboard data
    python analyze.py --year all        # Analyze all years, update all dashboard data
"""
import argparse
import csv
import glob
import json
import os
import re
from collections import defaultdict
from typing import List

from spending.models import Transaction
from spending.parsers import auto_parse
from spending.rules import apply_categories, generate_ids, tag_reimbursable, tag_not_spending
from spending.filters import detect_internal_transfers, detect_refunds, apply_final_filters
from spending.dashboard_template import generate_data_js, generate_manifest_js, generate_dashboard_shell

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')
OUTPUT_DIR = os.path.join(BASE_DIR, 'output')


OVERRIDES_PATH = os.path.join(OUTPUT_DIR, 'overrides.json')


def load_overrides() -> dict:
    """Load overrides.json if it exists, return empty structure otherwise."""
    if os.path.isfile(OVERRIDES_PATH):
        with open(OVERRIDES_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {'reimbursable': {}, 'notSpending': {}, 'categories': {}}


def apply_overrides(transactions: List['Transaction'], overrides: dict) -> None:
    """Apply manual overrides from overrides.json to transactions in-place."""
    reimb = overrides.get('reimbursable', {})
    ns = overrides.get('notSpending', {})
    cats = overrides.get('categories', {})

    txn_map = {t.txn_id: t for t in transactions}
    for tid, val in reimb.items():
        if tid in txn_map:
            txn_map[tid].is_reimbursable = val
    for tid, val in ns.items():
        if tid in txn_map:
            txn_map[tid].is_not_spending = val
    for tid, val in cats.items():
        if tid in txn_map:
            txn_map[tid].category = val


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
    tag_not_spending(final_txns)

    # Apply manual overrides from overrides.json
    overrides = load_overrides()
    apply_overrides(final_txns, overrides)

    print(f"[{year}] Final count: {len(final_txns)}")
    return final_txns


def generate_static_reports(transactions: List[Transaction], output_subdir: str, title: str) -> None:
    """Generate Markdown report and CSV summary."""
    os.makedirs(output_subdir, exist_ok=True)
    
    # Report
    report_path = os.path.join(output_subdir, 'spending_report.md')
    total_spending = sum(t.amount for t in transactions)
    # ... (Simplified reporting logic for brevity, or full implementation) ...
    # For now, I'll include the full reporting logic to preserve functionality
    
    monthly_spending = defaultdict(float)
    source_spending = defaultdict(float)
    category_spending = defaultdict(float)

    for t in transactions:
        monthly_spending[t.month] += t.amount
        source_spending[t.source] += t.amount
        category_spending[t.category] += t.amount

    sorted_by_amount = sorted(transactions, key=lambda t: t.amount, reverse=True)

    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(f"# {title}\n\n")
        f.write(f"**Total Net Spending**: ${total_spending:,.2f}\n\n")

        f.write("## Monthly Breakdown\n")
        f.write("| Month | Spending |\n|---|---|\n")
        for month in sorted(monthly_spending.keys()):
            f.write(f"| {month} | ${monthly_spending[month]:,.2f} |\n")
        f.write("\n")

        f.write("## Top Categories\n")
        f.write("| Category | Spending |\n|---|---|\n")
        sorted_cats = sorted(category_spending.items(), key=lambda x: x[1], reverse=True)
        for cat, amt in sorted_cats[:15]:
            f.write(f"| {cat} | ${amt:,.2f} |\n")
        f.write("\n")
        
        f.write("## Top 10 Expenses\n")
        f.write("| Date | Description | Amount |\n|---|---|---|\n")
        for t in sorted_by_amount[:10]:
            f.write(f"| {t.date} | {t.description[:40]} | ${t.amount:,.2f} |\n")

    print(f"Report saved to: {report_path}")

    # CSV
    csv_path = os.path.join(output_subdir, 'spending_summary.csv')
    fieldnames = ['Date', 'Description', 'Category', 'Amount', 'Source', 'TxnID', 'IsReimbursable']
    try:
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
            writer.writeheader()
            for t in transactions:
                row = t.to_dict()
                row['Date'] = t.date.strftime('%Y-%m-%d')
                writer.writerow(row)
        print(f"CSV saved to: {csv_path}")
    except Exception as e:
        print(f"Error saving CSV: {e}")


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
        print(f"\n--- Processing {year} ---")
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
    # Find all generated data files to build manifest
    search_path = os.path.join(OUTPUT_DIR, 'data_*.js')
    found_files = glob.glob(search_path)
    available_years = []
    for f in found_files:
        match = re.search(r'data_(\d+)\.js', os.path.basename(f))
        if match:
            available_years.append(match.group(1))
    
    available_years.sort()
    
    print("\n--- Updating Dashboard ---")
    generate_manifest_js(available_years, OUTPUT_DIR)
    generate_dashboard_shell(OUTPUT_DIR)


if __name__ == "__main__":
    main()
