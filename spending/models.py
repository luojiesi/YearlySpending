"""
Transaction data model — the consistent data structure used across all years.
"""
from dataclasses import dataclass, field, asdict
from datetime import datetime
import hashlib


@dataclass
class Transaction:
    """A single financial transaction."""
    date: datetime
    description: str
    amount: float            # Standardized: positive = spending, negative = credit
    category: str = 'Uncategorized'
    source: str = ''         # e.g. "Chase", "BOA-4364", "Amex"
    source_file: str = ''
    is_spending: bool = True
    is_internal_transfer: bool = False
    is_refunded: bool = False
    is_reimbursable: bool = False
    is_not_spending: bool = False
    txn_id: str = ''

    @property
    def month(self) -> str:
        """Returns YYYY-MM string."""
        return self.date.strftime('%Y-%m')

    @property
    def year(self) -> int:
        return self.date.year

    def generate_id(self, index: int = 0):
        """Generate a stable MD5-based ID from key fields.

        The index parameter disambiguates otherwise-identical transactions
        (e.g., two identical purchases on the same day from the same source).
        """
        unique_str = f"{self.date}{self.description}{self.amount}{self.source}{index}"
        self.txn_id = hashlib.md5(unique_str.encode('utf-8')).hexdigest()

    def to_dict(self) -> dict:
        """Convert to a plain dict for JSON/CSV serialization."""
        return {
            'Date': self.date,
            'Description': self.description,
            'Category': self.category,
            'Amount': self.amount,
            'Source': self.source,
            'SourceFile': self.source_file,
            'IsSpending': self.is_spending,
            'IsInternalTransfer': self.is_internal_transfer,
            'IsRefunded': self.is_refunded,
            'IsReimbursable': self.is_reimbursable,
            'TxnID': self.txn_id,
        }

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
            'IsNotSpending': self.is_not_spending,
        }
