"""CSV report tokenizer + money parsing for QuickBooks report exports.

QuickBooks report CSVs are banded like the on-screen report: a title/period row,
section headers (amount cell blank), account rows (name, amount), and subtotal /
total control rows. Fields are quoted, and some account names contain commas
(e.g. "Licenses, Permits,Other Taxes"), so cells are parsed with the csv module,
never a naive split.

Byte-addressed no-loss (I1): rows are split on the raw bytes so ``raw_line_text``
is the verbatim decode of ``bytes[start:end]`` and cell parsing is applied to that
exact line.
"""
from __future__ import annotations

import csv
from decimal import Decimal, InvalidOperation

from app.connectors.base import TokenizedCell, TokenizedRow


def parse_money(text: str) -> Decimal:
    """Parse a QuickBooks money cell to an exact Decimal.

    Handles thousands separators, currency symbols, and parenthesized negatives
    ``(1,234.56)`` -> -1234.56. Raises ValueError on anything non-numeric so the
    caller can quarantine the row rather than silently coerce to zero.
    """
    s = (text or '').strip().strip('"').strip()
    if s == '':
        raise ValueError('empty money cell')
    negative = s.startswith('(') and s.endswith(')')
    if negative:
        s = s[1:-1]
    s = s.replace('$', '').replace(',', '').replace(' ', '')
    if s.startswith('-'):
        negative = True
        s = s[1:]
    try:
        value = Decimal(s)
    except (InvalidOperation, ValueError):
        raise ValueError(f'not a money value: {text!r}')
    return -value if negative else value


def looks_like_money(text: str) -> bool:
    try:
        parse_money(text)
        return True
    except ValueError:
        return False


def tokenize_csv(raw_bytes: bytes) -> tuple[list, str]:
    """Return (rows, encoding). Each physical line -> one verbatim TokenizedRow with
    cells parsed by the csv module. QuickBooks report CSVs do not embed newlines in
    fields, so per-line parsing is safe."""
    try:
        raw_bytes.decode('utf-8')
        encoding = 'utf-8'
    except UnicodeDecodeError:
        encoding = 'cp1252'

    rows: list = []
    offset = 0
    row_index = 0
    for seg in raw_bytes.split(b'\n'):
        start = offset
        end = offset + len(seg)
        offset = end + 1
        text = seg.decode(encoding)               # verbatim (may keep trailing '\r')
        content = text.rstrip('\r')
        try:
            fields = next(csv.reader([content])) if content else []
        except StopIteration:
            fields = []
        cells = [TokenizedCell(col_index=i, raw_value=v) for i, v in enumerate(fields)]
        record_type = 'blank' if content.strip() == '' else 'data'
        rows.append(TokenizedRow(
            row_index=row_index, raw_line_text=text,
            byte_offset_start=start, byte_offset_end=end,
            band='', record_type=record_type, cells=cells,
        ))
        row_index += 1
    return rows, encoding
