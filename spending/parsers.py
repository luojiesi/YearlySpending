"""
Parsers for different bank statement formats.
Each parser reads a CSV file and returns a list of Transaction objects.
"""
import csv
import os
from datetime import datetime
from .models import Transaction


def parse_float(val: str) -> float:
    """Safely parse a monetary string to float."""
    try:
        if val:
            return float(val.replace(',', '').replace('"', '').replace('$', ''))
        return 0.0
    except ValueError:
        return 0.0


def _chase_source_name(file_path: str) -> str:
    """Derive source name from Chase filename, e.g. 'Chase_9300.csv' -> 'Chase-9300'."""
    import re
    basename = os.path.splitext(os.path.basename(file_path))[0]
    match = re.search(r'[Cc]hase[_-](\w+)', basename)
    if match:
        return f'Chase-{match.group(1)}'
    return 'Chase'


def parse_chase(file_path: str) -> list[Transaction]:
    """Parse a Chase credit card CSV export."""
    transactions = []
    source_name = _chase_source_name(file_path)
    try:
        with open(file_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get('Type') == 'Payment':
                    continue

                amount = parse_float(row.get('Amount', '0')) * -1  # Chase: negative = spending

                try:
                    date_obj = datetime.strptime(row.get('Transaction Date', ''), '%m/%d/%Y')
                except (ValueError, TypeError):
                    continue

                transactions.append(Transaction(
                    date=date_obj,
                    description=row.get('Description', ''),
                    category=row.get('Category', 'Uncategorized'),
                    amount=amount,
                    source=source_name,
                    source_file=os.path.basename(file_path),
                    is_spending=True,
                    is_internal_transfer=False,
                ))
    except Exception as e:
        print(f"Error parsing Chase file {file_path}: {e}")
    return transactions


def parse_amex(file_path: str) -> list[Transaction]:
    """Parse an American Express CSV export."""
    transactions = []
    try:
        with open(file_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                desc = row.get('Description', '')
                if 'AUTOPAY' in desc.upper() or 'PAYMENT' in desc.upper():
                    continue

                amount = parse_float(row.get('Amount', '0'))

                try:
                    date_obj = datetime.strptime(row.get('Date', ''), '%m/%d/%Y')
                except (ValueError, TypeError):
                    continue

                transactions.append(Transaction(
                    date=date_obj,
                    description=desc,
                    category='Uncategorized',
                    amount=amount,
                    source='Amex',
                    source_file=os.path.basename(file_path),
                    is_spending=True,
                    is_internal_transfer=False,
                ))
    except Exception as e:
        print(f"Error parsing Amex file {file_path}: {e}")
    return transactions


def parse_boa(file_path: str) -> list[Transaction]:
    """Parse a Bank of America checking account CSV export."""
    transactions = []
    try:
        with open(file_path, 'r', encoding='utf-8-sig') as f:
            lines = f.readlines()
            if len(lines) < 7:
                return []

            # Extract account digits from header
            source_name = 'BOA'
            for line in lines:
                if 'Account last digit' in line:
                    parts = line.split(',')
                    if len(parts) >= 2:
                        digit = parts[1].strip()
                        source_name = f'BOA-{digit}'
                    break

            # Find header row dynamically
            header_row_index = -1
            for i, line in enumerate(lines):
                if line.strip().startswith('Date') or 'Date,Description' in line:
                    header_row_index = i
                    break

            if header_row_index == -1:
                return []

            reader = csv.DictReader(lines[header_row_index:])

            # Keywords indicating CC autopay or internal transfers
            exclude_keywords = [
                'CHASE CREDIT CRD', 'American Express', 'AMEX',
                'CAPITAL ONE', 'CITI CARD', 'DISCOVER', 'FID BKG SVC LLC'
            ]

            for row in reader:
                desc = row.get('Description', '')
                val = parse_float(row.get('Amount', '0'))
                amount = val * -1  # BoA: negative CSV = debit = positive spending

                # Determine spending
                is_spending = amount > 0

                # Explicit excludes
                if 'Online Banking transfer' in desc:
                    is_spending = False
                if 'Online scheduled transfer to CHK' in desc:
                    is_spending = False

                # CC autopay keywords
                for kw in exclude_keywords:
                    if kw.lower() in desc.lower():
                        is_spending = False
                        break

                try:
                    date_obj = datetime.strptime(row.get('Date', ''), '%m/%d/%Y')
                except (ValueError, TypeError):
                    continue

                transactions.append(Transaction(
                    date=date_obj,
                    description=desc,
                    category='Uncategorized',
                    amount=amount,
                    source=source_name,
                    source_file=os.path.basename(file_path),
                    is_spending=is_spending,
                    is_internal_transfer=False,
                ))
    except Exception as e:
        print(f"Error parsing BOA file {file_path}: {e}")
    return transactions


def auto_parse(file_path: str) -> list[Transaction]:
    """Auto-detect file format from filename and parse accordingly."""
    fname = os.path.basename(file_path).lower()

    if 'chase' in fname:
        return parse_chase(file_path)
    elif 'amex' in fname or ('activity' in fname and 'chase' not in fname):
        return parse_amex(file_path)
    elif 'boa' in fname or 'stmt' in fname:
        return parse_boa(file_path)
    else:
        print(f"Skipping unknown file format: {os.path.basename(file_path)}")
        return []
