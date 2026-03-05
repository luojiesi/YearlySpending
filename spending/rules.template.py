"""
Business rules: categorization, tax exclusion, reimbursable tagging.
These rules apply across all years.

HOW TO USE THIS TEMPLATE:
1. Rename or copy this file to `rules.py`
2. Customize `TAX_KEYWORDS`, `CATEGORY_RULES`, and `REIMBURSABLE_KEYWORDS` to match your own bank statement descriptions.
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

def _match_special_insurance(desc: str) -> str | None:
    """Example of a dynamic category function."""
    if 'SOME_INSURANCE' not in desc:
        return None
    try:
        parts = desc.split('INDN:')
        if len(parts) > 1:
            name_part = parts[1].split('CO ID')[0].strip()
            if 'USER1' in name_part:
                return 'Insurance - User 1'
            elif 'USER2' in name_part:
                return 'Insurance - User 2'
    except Exception:
        pass
    return 'Insurance'


CATEGORY_RULES = [
    # (match_fn(desc_upper) -> bool/str, category_name or None if fn returns str)
    (lambda d: 'HOA PAYMENT' in d, 'HOA'),
    (lambda d: 'RENTAL MGMT' in d, 'Rental Management Fee'),
    # Dynamic category example:
    (lambda d: _match_special_insurance(d) if 'SOME_INSURANCE' in d else False, None),
    (lambda d: 'HOME MTG' in d and '12345' in d, 'Mortgage - House 1'),
    (lambda d: 'DAYCARE' in d, 'Daycare'),
    (lambda d: 'WIRE TYPE:INTL OUT' in d, 'Wire Transfer'),
    (lambda d: 'ELECTRIC CO' in d, 'Bills & Utilities'),
    (lambda d: 'PTY TAX' in d or 'COUNTY PROPERTY' in d, 'Property Tax'),
]


def apply_categories(transactions: list[Transaction]) -> None:
    """Apply custom categorization rules to transactions (in-place)."""
    for txn in transactions:
        desc_upper = txn.description.upper()

        # Check static and dynamic rules
        for match_fn, category in CATEGORY_RULES:
            result = match_fn(desc_upper)
            if result:
                # If category is None, the match_fn itself returned the category string
                txn.category = result if category is None else category
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
REIMBURSABLE_KEYWORDS = ['EMPLOYER_REIMBURSEMENT', 'SOME_BILL_SPLIT']


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
