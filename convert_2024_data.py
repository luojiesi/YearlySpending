"""
Convert 2024 raw data files into parser-compatible CSVs for data/2024/.

Sources:
  - all_expenses_jan-june2024.xlsx - all_credit_cards.csv  (Jan-June 2024 credit cards)
  - all_expenses_20240701_20250607.xlsx - all.csv           (Jul 2024 - Jun 2025 all accounts)
  - BOA_4364stmt.csv                                        (Jan-June 2024 BOA 4364)
  - eStmt_*.pdf                                             (BOA 4377 statements)

Outputs (in data/2024/):
  - Chase_9300.csv   (ChaseSapphire)
  - Chase_7179.csv   (ChaseJiesi)
  - Amex.csv
  - BOA_4364.csv
  - BOA_4377.csv
"""
import csv
import os
import re
import glob
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RAW_DIR = os.path.join(BASE_DIR, 'data', 'Raw')
OUTPUT_DIR = os.path.join(BASE_DIR, 'data', '2024')

JAN_JUNE_CSV = os.path.join(RAW_DIR, 'all_expenses_jan-june2024.xlsx - all_credit_cards.csv')
JUL_DEC_CSV = os.path.join(RAW_DIR, 'all_expenses_20240701_20250607.xlsx - all.csv')
BOA_4364_CSV = os.path.join(RAW_DIR, 'BOA_4364stmt.csv')
PDF_DIR = RAW_DIR  # eStmt_*.pdf files are here


def is_2024_date(date_str):
    """Check if a date string refers to year 2024."""
    if not date_str or not date_str.strip():
        return False
    try:
        for fmt in ('%m/%d/%Y', '%m/%d/%y'):
            try:
                dt = datetime.strptime(date_str.strip(), fmt)
                return dt.year == 2024
            except ValueError:
                continue
    except Exception:
        pass
    return False


def get_best_date(row):
    """Get the best available date from a row, preferring Post Date as fallback."""
    txn_date = (row.get('Transaction Date') or '').strip()
    post_date = (row.get('Post Date') or '').strip()
    # Use Transaction Date if available, else Post Date
    return txn_date if txn_date else post_date


def normalize_date(date_str):
    """Normalize date to M/D/YYYY format for consistency with parser expectations."""
    if not date_str:
        return ''
    date_str = date_str.strip()
    for fmt in ('%m/%d/%Y', '%m/%d/%y'):
        try:
            dt = datetime.strptime(date_str, fmt)
            return dt.strftime('%-m/%d/%Y') if os.name != 'nt' else dt.strftime('%#m/%d/%Y')
        except ValueError:
            continue
    return date_str


def normalize_date_simple(date_str):
    """Normalize to M/D/YYYY, Windows-compatible."""
    if not date_str:
        return ''
    date_str = date_str.strip()
    for fmt in ('%m/%d/%Y', '%m/%d/%y'):
        try:
            dt = datetime.strptime(date_str, fmt)
            # Manually format without leading zeros
            return f'{dt.month}/{dt.day}/{dt.year}'
        except ValueError:
            continue
    return date_str


# ──────────────────────────────────────────────
# Credit Card Extraction (Chase + Amex)
# ──────────────────────────────────────────────

def read_jan_june_credit_cards():
    """Read Jan-June 2024 credit card CSV.
    Columns: Transaction Date,Post Date,Description,Category,Cuttable,Type,Amount,Card
    """
    rows = {'ChaseSapphire': [], 'ChaseJiesi': [], 'Amex': []}
    with open(JAN_JUNE_CSV, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            card = (row.get('Card') or '').strip()
            if card not in rows:
                continue
            date = get_best_date(row)
            if not is_2024_date(date):
                continue
            rows[card].append(row)
    return rows


def read_jul_dec_credit_cards():
    """Read Jul-Dec 2024 credit card + BOA entries from the all_expenses CSV.
    Columns: Transaction Date,Post Date,Description,Category,Type,Amount,Card,Time
    """
    rows = {'ChaseSapphire': [], 'ChaseJiesi': [], 'Amex': [],
            'BOA_4364': [], 'BOA_4377': []}
    with open(JUL_DEC_CSV, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            card = (row.get('Card') or '').strip()
            if card not in rows:
                continue
            date = get_best_date(row)
            if not is_2024_date(date):
                continue
            rows[card].append(row)
    return rows


def write_chase_csv(filename, rows_jan_june, rows_jul_dec, card_name):
    """Write Chase-format CSV: Transaction Date,Post Date,Description,Category,Type,Amount,Memo"""
    output_path = os.path.join(OUTPUT_DIR, filename)
    all_rows = []

    # Jan-June rows (has Cuttable column we skip)
    for row in rows_jan_june:
        txn_date = normalize_date_simple(get_best_date(row))
        post_date = normalize_date_simple((row.get('Post Date') or '').strip())
        all_rows.append({
            'Transaction Date': txn_date,
            'Post Date': post_date if post_date else txn_date,
            'Description': (row.get('Description') or '').strip(),
            'Category': (row.get('Category') or '').strip(),
            'Type': (row.get('Type') or '').strip(),
            'Amount': (row.get('Amount') or '').strip(),
            'Memo': '',
        })

    # Jul-Dec rows
    for row in rows_jul_dec:
        txn_date = normalize_date_simple(get_best_date(row))
        post_date = normalize_date_simple((row.get('Post Date') or '').strip())
        all_rows.append({
            'Transaction Date': txn_date,
            'Post Date': post_date if post_date else txn_date,
            'Description': (row.get('Description') or '').strip(),
            'Category': (row.get('Category') or '').strip(),
            'Type': (row.get('Type') or '').strip(),
            'Amount': (row.get('Amount') or '').strip(),
            'Memo': '',
        })

    # Sort by date
    def sort_key(r):
        try:
            return datetime.strptime(r['Transaction Date'], '%m/%d/%Y')
        except:
            return datetime.min
    all_rows.sort(key=sort_key)

    fieldnames = ['Transaction Date', 'Post Date', 'Description', 'Category', 'Type', 'Amount', 'Memo']
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_rows)

    print(f"  {filename}: {len(all_rows)} transactions")
    return len(all_rows)


def write_amex_csv(rows_jan_june, rows_jul_dec):
    """Write Amex-format CSV: Date,Description,Amount"""
    output_path = os.path.join(OUTPUT_DIR, 'Amex.csv')
    all_rows = []

    for row in list(rows_jan_june) + list(rows_jul_dec):
        date = normalize_date_simple(get_best_date(row))
        desc = (row.get('Description') or '').strip()
        amount_str = (row.get('Amount') or '').strip()
        # Invert sign: raw 2024 data has negative for spending,
        # but 2025 Amex format (and parse_amex) expects positive for spending
        try:
            amount_val = float(amount_str.replace(',', ''))
            amount_out = f'{amount_val * -1:.2f}'
        except ValueError:
            amount_out = amount_str
        all_rows.append({
            'Date': date,
            'Description': desc,
            'Amount': amount_out,
        })

    # Sort by date
    def sort_key(r):
        try:
            return datetime.strptime(r['Date'], '%m/%d/%Y')
        except:
            return datetime.min
    all_rows.sort(key=sort_key)

    fieldnames = ['Date', 'Description', 'Amount']
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_rows)

    print(f"  Amex.csv: {len(all_rows)} transactions")
    return len(all_rows)


# ──────────────────────────────────────────────
# BOA 4364 Extraction
# ──────────────────────────────────────────────

def parse_boa_4364_stmt():
    """Parse the BOA_4364stmt.csv (Jan-June 2024).
    Format: Date,Description,Date,Description,Type,Amount,Balance,Status
    The first Date and Description columns are the ones we want.
    Amount format: ($123.45) for debits, $123.45 for credits.
    """
    rows = []
    with open(BOA_4364_CSV, 'r', encoding='utf-8-sig') as f:
        reader = csv.reader(f)
        header = next(reader)  # skip header

        for raw_row in reader:
            if len(raw_row) < 6:
                continue

            date_str = raw_row[0].strip()
            description = raw_row[1].strip()
            amount_str = raw_row[5].strip()

            if not date_str or not amount_str:
                continue

            # Check it's 2024
            if not is_2024_date(date_str):
                continue

            # Clean amount: ($1,234.56) -> -1234.56, $1,234.56 -> 1234.56
            amount_clean = amount_str.replace('$', '').replace(',', '').replace(' ', '')
            if amount_clean.startswith('(') and amount_clean.endswith(')'):
                amount_clean = '-' + amount_clean[1:-1]

            try:
                amount_val = float(amount_clean)
            except ValueError:
                continue

            rows.append({
                'Date': normalize_date_simple(date_str),
                'Description': description,
                'Amount': f'{amount_val:.2f}',
            })

    return rows


def write_boa_csv(filename, digit, rows):
    """Write BOA-format CSV with header block expected by parse_boa."""
    output_path = os.path.join(OUTPUT_DIR, filename)

    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        # Write header block that parse_boa expects
        f.write(f'Account last digit,{digit}\n')
        f.write(',,\n')
        f.write(',,\n')
        f.write(',,\n')
        f.write(',,\n')
        f.write(',,\n')

        # Write transaction CSV
        writer = csv.DictWriter(f, fieldnames=['Date', 'Description', 'Amount', 'Running Bal.'])
        writer.writeheader()
        for row in rows:
            writer.writerow({
                'Date': row['Date'],
                'Description': row['Description'],
                'Amount': row['Amount'],
                'Running Bal.': '',
            })

    print(f"  {filename}: {len(rows)} transactions")
    return len(rows)


# ──────────────────────────────────────────────
# BOA PDF Extraction (shared helper)
# ──────────────────────────────────────────────

# Lines starting with these prefixes are NOT continuation lines
_SKIP_PREFIXES = (
    'Total', 'Page', 'Date Description', 'Date Amount',
    'continued', 'MR ', 'IMPORTANT', 'Deposits and',
    'Withdrawals and', 'How to', 'Updating', 'Deposit agreement',
    'Electronic transfers', 'Reporting', 'Direct deposits',
    'Braille', 'bankofamerica', 'BANK DEPOSIT',
)


def _is_continuation_line(line):
    """Check if a line is a continuation of a previous transaction description."""
    if not line:
        return False
    # Date line = new transaction, not a continuation
    if re.match(r'^\d{2}/\d{2}/\d{2}\s', line):
        return False
    # Known non-transaction lines
    for prefix in _SKIP_PREFIXES:
        if line.startswith(prefix):
            return False
    # Copyright line
    if line.startswith('\xa9') or 'Bank of America' in line:
        return False
    # Section headers with $ totals (e.g. "Total deposits ... $105,832.49")
    if line.startswith('$') or line.endswith('$'):
        return False
    # Looks like a bullet point or legal text
    if line.startswith('- ') or line.startswith('You '):
        return False
    return True


def _extract_boa_txns_from_pdfs(glob_pattern):
    """Extract transactions from BOA eStmt PDF files, joining multi-line descriptions.

    BOA PDFs often split transaction descriptions across multiple lines. For example:
        03/20/24 SO CAL EDISON CO DES:DIRECTPAY ID:700750501269 INDN:XIN XIE CO -334.99
        ID:0088778600 PPD

    This function matches the first line (date + desc + amount) and then appends
    any continuation lines to the description.
    """
    import pdfplumber

    pdf_files = sorted(glob.glob(os.path.join(PDF_DIR, glob_pattern)))
    print(f"\n  Found {len(pdf_files)} PDF files")

    all_txns = []
    txn_pattern = re.compile(
        r'^(\d{2}/\d{2}/\d{2})\s+'  # date MM/DD/YY
        r'(.+?)\s+'                  # description (lazy to leave amount)
        r'(-?[\d,]+\.\d{2})$'        # amount at end of line
    )

    for pdf_path in pdf_files:
        pdf_name = os.path.basename(pdf_path)
        count = 0

        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if not text:
                    continue

                lines = text.split('\n')
                # current_txn holds the in-progress transaction dict (or None)
                current_txn = None

                for line in lines:
                    line = line.strip()
                    match = txn_pattern.match(line)

                    if match:
                        # Flush previous transaction
                        if current_txn:
                            all_txns.append(current_txn)
                            count += 1

                        date_str = match.group(1)
                        desc = match.group(2).strip()
                        amount_str = match.group(3).replace(',', '')

                        try:
                            dt = datetime.strptime(date_str, '%m/%d/%y')
                        except ValueError:
                            current_txn = None
                            continue

                        try:
                            amount = float(amount_str)
                        except ValueError:
                            current_txn = None
                            continue

                        if dt.year != 2024:
                            current_txn = None
                            continue

                        current_txn = {
                            'Date': f'{dt.month}/{dt.day}/{dt.year}',
                            'Description': desc,
                            'Amount': f'{amount:.2f}',
                            'source_pdf': pdf_name,
                        }

                    elif current_txn and _is_continuation_line(line):
                        # Append continuation line to the current transaction's description
                        current_txn['Description'] += ' ' + line

                    else:
                        # Non-transaction line — flush current if any
                        if current_txn:
                            all_txns.append(current_txn)
                            count += 1
                            current_txn = None

                # Flush last transaction on the page
                if current_txn:
                    all_txns.append(current_txn)
                    count += 1
                    current_txn = None

        print(f"    {pdf_name}: {count} transactions extracted")

    return all_txns


def extract_boa_4377_from_pdfs():
    """Extract transactions from BOA 4377 eStmt PDF files."""
    return _extract_boa_txns_from_pdfs('BOA_4377_eStmt_*.pdf')


def extract_boa_4364_from_pdfs():
    """Extract transactions from BOA 4364 eStmt PDF files."""
    return _extract_boa_txns_from_pdfs('BOA_4364_eStmt_*.pdf')

    return all_txns


def extract_boa_4377_from_csv(jul_dec_rows):
    """Convert BOA_4377 rows from the all_expenses CSV into BOA format."""
    rows = []
    for row in jul_dec_rows:
        date = normalize_date_simple(get_best_date(row))
        desc = (row.get('Description') or '').strip()
        amount_str = (row.get('Amount') or '').strip()

        # Clean amount (may have quotes/commas)
        amount_clean = amount_str.replace('"', '').replace(',', '')
        try:
            amount = float(amount_clean)
        except ValueError:
            continue

        rows.append({
            'Date': date,
            'Description': desc,
            'Amount': f'{amount:.2f}',
        })
    return rows


def verify_boa_4377(pdf_txns, csv_txns):
    """Cross-verify BOA 4377 data between PDF and CSV sources for overlapping period."""
    print("\n" + "=" * 70)
    print("BOA 4377 CROSS-VERIFICATION (PDF vs CSV)")
    print("=" * 70)

    # Build date-indexed sets for comparison (Jul-Dec 2024 only)
    def parse_date(d):
        try:
            return datetime.strptime(d, '%m/%d/%Y')
        except:
            return None

    # Filter to Jul-Dec 2024 for both
    pdf_jul_dec = []
    for t in pdf_txns:
        dt = parse_date(t['Date'])
        if dt and dt.year == 2024 and dt.month >= 7:
            pdf_jul_dec.append(t)

    csv_jul_dec = []
    for t in csv_txns:
        dt = parse_date(t['Date'])
        if dt and dt.year == 2024 and dt.month >= 7:
            csv_jul_dec.append(t)

    print(f"\nPDF Jul-Dec 2024 transactions: {len(pdf_jul_dec)}")
    print(f"CSV Jul-Dec 2024 transactions: {len(csv_jul_dec)}")

    # Build sets using (date, amount) as key for matching
    def make_key(t):
        return (t['Date'], t['Amount'])

    pdf_keys = {}
    for t in pdf_jul_dec:
        k = make_key(t)
        pdf_keys.setdefault(k, []).append(t)

    csv_keys = {}
    for t in csv_jul_dec:
        k = make_key(t)
        csv_keys.setdefault(k, []).append(t)

    # Find matches and mismatches
    matched = 0
    pdf_only = []
    csv_only = []

    all_keys = set(list(pdf_keys.keys()) + list(csv_keys.keys()))
    for k in sorted(all_keys):
        pdf_count = len(pdf_keys.get(k, []))
        csv_count = len(csv_keys.get(k, []))
        min_count = min(pdf_count, csv_count)
        matched += min_count
        if pdf_count > csv_count:
            for t in pdf_keys[k][csv_count:]:
                pdf_only.append(t)
        elif csv_count > pdf_count:
            for t in csv_keys[k][pdf_count:]:
                csv_only.append(t)

    print(f"\nMatched (date+amount): {matched}")

    if pdf_only:
        print(f"\nWARNING: {len(pdf_only)} transactions in PDF ONLY (not in CSV):")
        for t in pdf_only[:20]:
            print(f"    {t['Date']}  {t['Amount']:>12}  {t['Description'][:60]}")
        if len(pdf_only) > 20:
            print(f"    ... and {len(pdf_only) - 20} more")

    if csv_only:
        print(f"\nWARNING: {len(csv_only)} transactions in CSV ONLY (not in PDF):")
        for t in csv_only[:20]:
            print(f"    {t['Date']}  {t['Amount']:>12}  {t['Description'][:60]}")
        if len(csv_only) > 20:
            print(f"    ... and {len(csv_only) - 20} more")

    if not pdf_only and not csv_only:
        print("\nOK: PERFECT MATCH — PDF and CSV sources agree completely for Jul-Dec 2024!")
    else:
        print(f"\n-> Differences found. The final BOA_4377.csv will use PDF data (more complete).")

    print("=" * 70)


# ──────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    print(f"Output directory: {OUTPUT_DIR}\n")

    # ── 1. Read source CSVs ──
    print("Reading Jan-June 2024 credit cards CSV...")
    jan_june = read_jan_june_credit_cards()
    for card, rows in jan_june.items():
        print(f"  {card}: {len(rows)} rows")

    print("\nReading Jul-Dec+ all_expenses CSV...")
    jul_dec = read_jul_dec_credit_cards()
    for card, rows in jul_dec.items():
        print(f"  {card}: {len(rows)} rows")

    # ── 2. Write Credit Card CSVs ──
    print("\nWriting credit card CSVs...")
    write_chase_csv('Chase_9300.csv', jan_june.get('ChaseSapphire', []), jul_dec.get('ChaseSapphire', []), 'ChaseSapphire')
    write_chase_csv('Chase_7179.csv', jan_june.get('ChaseJiesi', []), jul_dec.get('ChaseJiesi', []), 'ChaseJiesi')
    write_amex_csv(jan_june.get('Amex', []), jul_dec.get('Amex', []))

    # ── 3. BOA 4364 (from PDFs) ──
    print("\nProcessing BOA 4364...")
    pdf_4364_txns = extract_boa_4364_from_pdfs()
    print(f"  Total from PDFs: {len(pdf_4364_txns)} transactions")

    # Sort by date
    def sort_by_date(r):
        try:
            return datetime.strptime(r['Date'], '%m/%d/%Y')
        except:
            return datetime.min

    for t in pdf_4364_txns:
        t.pop('source_pdf', None)
    pdf_4364_txns.sort(key=sort_by_date)
    write_boa_csv('BOA_4364.csv', '4364', pdf_4364_txns)

    # ── 4. BOA 4377 ──
    print("\nProcessing BOA 4377...")

    # Extract from PDFs (full year)
    pdf_txns = extract_boa_4377_from_pdfs()
    print(f"  Total from PDFs: {len(pdf_txns)} transactions")

    # Extract from CSV (Jul-Dec overlap)
    csv_4377_rows = extract_boa_4377_from_csv(jul_dec.get('BOA_4377', []))
    print(f"  Total from CSV: {len(csv_4377_rows)} transactions")

    # Cross-verify
    verify_boa_4377(pdf_txns, csv_4377_rows)

    # Use PDF data as primary (it covers full year)
    # Remove the source_pdf key before writing
    for t in pdf_txns:
        t.pop('source_pdf', None)
    pdf_txns.sort(key=sort_by_date)
    write_boa_csv('BOA_4377.csv', '4377', pdf_txns)

    # ── Summary ──
    print("\n" + "=" * 50)
    print("CONVERSION COMPLETE")
    print("=" * 50)
    print(f"\nOutput files in {OUTPUT_DIR}/:")
    for f in sorted(os.listdir(OUTPUT_DIR)):
        path = os.path.join(OUTPUT_DIR, f)
        if os.path.isfile(path):
            with open(path, 'r', encoding='utf-8') as fh:
                lines = fh.readlines()
            print(f"  {f}: {len(lines) - 1} data rows")  # subtract header/block


if __name__ == '__main__':
    main()
