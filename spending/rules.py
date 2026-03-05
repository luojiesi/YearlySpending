"""
Business rules: categorization, tax exclusion, reimbursable tagging.
These rules apply across all years.
"""
from .models import Transaction


# --- Tax Exclusion Keywords ---
# Income/estimated tax keywords only (property tax is real spending)
TAX_KEYWORDS = [
    'FRANCHISE TAX', 'IRS DES:', 'USATAXPYMT',
]


def is_tax_transaction(txn: Transaction) -> bool:
    """Check if a transaction is a tax payment."""
    desc = txn.description.upper()
    return any(kw in desc for kw in TAX_KEYWORDS)


# --- Custom Category Rules ---
# Each rule is a (match_function, category_name) tuple.
# Rules are checked in order; first match wins.

def _match_hoa_stjames(desc: str) -> bool:
    return ('CITY HEIGHTS AT' in desc and 'WEB PMTS' in desc) or \
           ('CLICKPAY' in desc and 'PROPRTYPAY' in desc)

def _match_rental_mgmt(desc: str) -> bool:
    return 'JOYHOME PROPERTY MANAGEMENT' in desc

def _match_transamerica(desc: str) -> str | None:
    """Returns specific category or None."""
    if 'TRANSAMERICA INS' not in desc:
        return None
    try:
        parts = desc.split('INDN:')
        if len(parts) > 1:
            name_part = parts[1].split('CO ID')[0].strip()
            if 'XIN' in name_part:
                return 'Long Term Insurance - Xin'
            elif 'JIESI' in name_part:
                return 'Long Term Insurance - Jiesi'
    except Exception:
        pass
    return 'Long Term Insurance'


CATEGORY_RULES = [
    # (match_fn(desc_upper) -> bool/str, category_name or None if fn returns str)
    (lambda d: _match_hoa_stjames(d), 'HOA - StJames'),
    (lambda d: _match_rental_mgmt(d), 'Rental Management Fee'),
    # Transamerica is special — handled separately below
    (lambda d: 'WF HOME MTG' in d and '27056' in d, 'Mortgage - CrystalSprings'),
    (lambda d: 'WF HOME MTG' in d and '24997' in d, 'Mortgage - StJames'),
    (lambda d: 'ICHA' in d and 'DES:' in d, 'Housing - 1407Cervantas'),
    (lambda d: 'UC REGENTS BILL PAYMENT' in d, 'Daycare'),
    (lambda d: 'MEIHUA' in d, 'Nanny'),
    (lambda d: 'WIRE TYPE:INTL OUT' in d, 'INIT Wire'),
    (lambda d: 'SO CAL EDISON' in d, 'Bills & Utilities'),
    (lambda d: 'PTY TAX' in d or 'SANTA CLARA DTAC' in d or ('ALAMEDA COUNTY' in d and 'WATER' not in d), 'Property Tax'),
]


def apply_categories(transactions: list[Transaction]) -> None:
    """Apply custom categorization rules to transactions (in-place)."""
    for txn in transactions:
        desc_upper = txn.description.upper()

        # Check Transamerica first (returns dynamic category)
        trans_cat = _match_transamerica(desc_upper)
        if trans_cat:
            txn.category = trans_cat
            continue

        # Check static rules
        for match_fn, category in CATEGORY_RULES:
            if match_fn(desc_upper):
                txn.category = category
                break


def generate_ids(transactions: list[Transaction]) -> None:
    """Generate stable TxnIDs for all transactions (in-place).

    Uses an index to disambiguate otherwise-identical transactions
    (same date, description, amount, source).
    """
    seen: dict[str, int] = {}
    for txn in transactions:
        key = f"{txn.date}{txn.description}{txn.amount}{txn.source}"
        index = seen.get(key, 0)
        seen[key] = index + 1
        txn.generate_id(index)


# --- Reimbursable Keywords ---
REIMBURSABLE_KEYWORDS = ['PROLIFIC_HW', 'ALAMEDA COUNTY WATER']


def tag_not_spending(transactions: list[Transaction]) -> None:
    """Auto-tag not-spending transactions (in-place). Tax payments are not spending."""
    for txn in transactions:
        if is_tax_transaction(txn):
            txn.is_not_spending = True


def tag_reimbursable(transactions: list[Transaction]) -> None:
    """Auto-tag reimbursable transactions (in-place)."""
    for txn in transactions:
        desc_upper = txn.description.upper()
        txn.is_reimbursable = any(kw in desc_upper for kw in REIMBURSABLE_KEYWORDS)
