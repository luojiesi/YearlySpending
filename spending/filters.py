"""
Filtering logic: cross-account transfer detection, refund matching, final filtering.
"""
from collections import defaultdict
from itertools import combinations
from .models import Transaction
from .rules import is_tax_transaction


def detect_internal_transfers(transactions: list[Transaction]) -> int:
    """
    Detect cross-account BOA transfers by matching identical dates with
    inverse amounts. Marks both sides as is_internal_transfer=True.
    Returns the number of matched pairs.
    """
    boa_txns = [t for t in transactions if t.source.startswith('BOA')]

    # Group by source file
    boa_files = defaultdict(list)
    for t in boa_txns:
        boa_files[t.source_file].append(t)

    if len(boa_files) < 2:
        return 0

    matches = 0
    for file_a, file_b in combinations(boa_files.keys(), 2):
        group_a = boa_files[file_a]
        group_b = boa_files[file_b]

        for a in group_a:
            if a.is_internal_transfer:
                continue

            target_amount = -1 * a.amount

            for b in group_b:
                if b.is_internal_transfer:
                    continue

                if b.date == a.date and abs(b.amount - target_amount) < 0.01:
                    a.is_internal_transfer = True
                    b.is_internal_transfer = True
                    matches += 1
                    print(f"  [Transfer] {a.date.date()} ${a.amount} <--> ${b.amount}")
                    break

    print(f"Found {matches} internal transfer pairs.")
    return matches


def detect_refunds(transactions: list[Transaction]) -> int:
    """
    Match credit card refunds with their original purchases.
    Only applies to Chase and Amex sources.
    Marks both sides as is_refunded=True.
    Returns the number of matched pairs.
    """
    by_source = defaultdict(list)
    for t in transactions:
        by_source[t.source].append(t)
        t.is_refunded = False  # Initialize

    match_count = 0
    for source, txns in by_source.items():
        # Only credit cards
        if not (source.startswith('Chase') or source.startswith('Amex')):
            continue

        credits = [t for t in txns if t.amount < 0]
        debits = [t for t in txns if t.amount > 0]
        debits.sort(key=lambda x: x.date)

        for credit in credits:
            target_amount = abs(credit.amount)
            refund_date = credit.date

            candidates = []
            for debit in debits:
                if debit.is_refunded or debit.is_internal_transfer:
                    continue
                if abs(debit.amount - target_amount) > 0.01:
                    continue
                if debit.date > refund_date:
                    continue
                if (refund_date - debit.date).days > 90:
                    continue
                candidates.append(debit)

            if candidates:
                best_match = candidates[-1]  # Closest to refund date
                credit.is_refunded = True
                best_match.is_refunded = True
                match_count += 1

    print(f"Found {match_count} refund pairs.")
    return match_count


def apply_final_filters(transactions: list[Transaction]) -> list[Transaction]:
    """
    Apply all exclusion filters and return the final clean list.
    Removes: internal transfers, refunds, non-spending, tax payments.
    """
    result = []
    for t in transactions:
        if t.is_internal_transfer:
            continue
        if t.is_refunded:
            continue
        if not t.is_spending:
            continue
        # Tax transactions are now kept and tagged as NotSpending instead
        result.append(t)
    return result
