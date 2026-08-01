"""IIF tokenizer: an Intuit Interchange File -> verbatim, byte-addressed rows.

IIF is tab-delimited and banded: a line starting ``!XXX`` is the column header
for record type ``XXX``; subsequent lines starting ``XXX`` are data rows of that
band (e.g. ``!ACCNT``/``ACCNT``, ``!VEND``/``VEND``). One file carries many bands.

Invariant support (I1): every physical line becomes exactly one TokenizedRow whose
``raw_line_text`` is the verbatim decode of ``bytes[start:end]`` and whose cells,
re-joined by tab, reconstruct ``raw_line_text`` exactly. Offsets index the ORIGINAL
bytes, so the round-trip is anchored to bytes, not a re-decode.
"""
from __future__ import annotations

from app.connectors.base import TokenizedCell, TokenizedRow


def detect_encoding(raw_bytes: bytes) -> str:
    """QuickBooks IIF is usually Windows-1252; try strict UTF-8 first. CP-1252
    maps every byte, so it is a lossless fallback (no round-trip loss)."""
    try:
        raw_bytes.decode('utf-8')
        return 'utf-8'
    except UnicodeDecodeError:
        return 'cp1252'


def tokenize_iif(raw_bytes: bytes) -> tuple[list, str]:
    """Return (rows, encoding). Rows are verbatim; band headers are tracked so each
    data row's cells carry their column names."""
    encoding = detect_encoding(raw_bytes)
    rows: list = []
    band_headers: dict = {}   # band -> header cell list (col names, index-aligned to data rows)
    offset = 0
    row_index = 0

    for seg in raw_bytes.split(b'\n'):
        start = offset
        end = offset + len(seg)
        offset = end + 1  # the '\n' that split() removed

        text = seg.decode(encoding)              # verbatim (may keep a trailing '\r')
        cells_raw = text.split('\t')             # split raw so rejoin == text exactly
        content = text.rstrip('\r')
        first = content.split('\t')[0] if content else ''

        if first.startswith('!'):
            band = first[1:]
            band_headers[band] = cells_raw
            record_type = 'header'
        elif content == '':
            band = ''
            record_type = 'blank'
        else:
            band = first
            record_type = 'data'

        header = band_headers.get(band, [])
        cells = [
            TokenizedCell(col_index=i, header_name=(header[i] if i < len(header) else ''), raw_value=v)
            for i, v in enumerate(cells_raw)
        ]
        rows.append(TokenizedRow(
            row_index=row_index, raw_line_text=text,
            byte_offset_start=start, byte_offset_end=end,
            band=band, record_type=record_type, cells=cells,
        ))
        row_index += 1

    return rows, encoding
