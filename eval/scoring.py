"""Execution-match scoring: two result sets are equivalent when they contain
the same rows, comparing column-order-sensitively but name-insensitively,
row-order-insensitively unless the question demands ordering, numerics rounded
to 2 decimals, NULLs as NULLs. This is the primary metric; a judge never
overrides an execution mismatch, it only explains one.
"""

from decimal import Decimal, InvalidOperation
import datetime


def _norm_cell(v):
    if v is None:
        return None
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float, Decimal)):
        try:
            return str(Decimal(str(v)).quantize(Decimal("0.01")))
        except InvalidOperation:
            return str(v)
    if isinstance(v, (datetime.date, datetime.datetime)):
        return v.isoformat()
    return str(v).strip()


def normalize(rows, ordered: bool):
    out = [tuple(_norm_cell(c) for c in row) for row in rows]
    if not ordered:
        out = sorted(out, key=lambda r: tuple("" if c is None else str(c) for c in r))
    return out


def execution_match(expected_rows, actual_rows, ordered: bool) -> bool:
    if expected_rows and actual_rows and len(expected_rows[0]) != len(actual_rows[0]):
        return False
    return normalize(expected_rows, ordered) == normalize(actual_rows, ordered)
