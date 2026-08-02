"""LLM invoice extraction -- the general path behind the deterministic parsers.

Reads ANY vendor's invoice PDF (Team Horner, Heritage-as-PDF, Home Depot, ...) via
Claude, classifies invoice-vs-noise, and returns a ParsedInvoice that flows into
the same vendor + product + price ledger. An arithmetic self-check gates every
invoice: only ones whose lines and totals reconcile are ingested; the rest are
flagged, never silently trusted (financial data).
"""
from __future__ import annotations

import hashlib
from datetime import date, datetime
from pathlib import Path

from sqlmodel import Session

from app.core import llm
from app.services.invoice_import import ParsedInvoice, ParsedLine, ingest_parsed_invoices

_SYSTEM = (
    "You extract structured data from a vendor PURCHASE invoice PDF (a bill the reader RECEIVED "
    "from a supplier). Return ONLY minified JSON with keys: is_invoice (bool), vendor_name, "
    "invoice_no, invoice_date (YYYY-MM-DD), currency, lines (array of {description, part_no, sku, "
    "qty, uom, unit_cost, ext_price}), subtotal, tax, total. unit_cost is the price PAID per unit "
    "(the net/cost price, NOT the retail/list/suggested price). Keep manufacturer part numbers in "
    "part_no. If the document is NOT a purchase invoice (a monthly statement summary, a safety "
    "manual, a submittal, an inspection report, a receipt for the reader's OWN software/subscription, "
    "a generic form), set is_invoice=false and all other fields null. Negative quantities/prices are "
    "credit memos -- keep them."
)
_USER = "Extract this document. Return only the JSON."

# Canonical vendor names so PDF-extracted names dedup to the existing vendor
# records (portal Heritage, Ace, etc.) rather than spawning near-duplicates.
_CANON = [
    ('heritage', 'Heritage Pool Supply'),
    ('strunk', 'Strunks Ace Hardware'),
    ('ace hardware', 'Strunks Ace Hardware'),
    ('team horner', 'Team Horner'),
    ('horner', 'Team Horner'),
    ('home depot', 'Home Depot'),
    ('aquacal', 'AquaCal'),
    ('fluidra', 'Fluidra'),
    ('poolcorp', 'PoolCorp'),
    ('scp', 'PoolCorp'),
    ('airgas', 'Airgas'),
]


def _norm_vendor(name: str) -> str:
    n = (name or '').strip().lower()
    for key, canon in _CANON:
        if key in n:
            return canon
    return (name or 'Unknown Vendor').strip().title()


def _f(v):
    try:
        return float(str(v).replace(',', '').replace('$', '').strip())
    except (TypeError, ValueError):
        return None


def _iso(v) -> date | None:
    try:
        return datetime.strptime(str(v).strip(), '%Y-%m-%d').date()
    except (TypeError, ValueError):
        return None


def extract_invoice_pdf(pdf_path, model: str | None = None) -> ParsedInvoice | None:
    """LLM-extract one invoice PDF. Returns None if the document is not an invoice."""
    data = llm.complete_json(_SYSTEM, _USER, pdf_bytes=Path(pdf_path).read_bytes(), model=model)
    if not data.get('is_invoice'):
        return None

    lines = []
    for ln in data.get('lines') or []:
        qty, unit, ext = _f(ln.get('qty')), _f(ln.get('unit_cost')), _f(ln.get('ext_price'))
        ok = (qty is not None and unit is not None and ext is not None
              and abs(qty * unit - ext) <= 0.02 * max(1.0, abs(ext)))
        lines.append(ParsedLine(
            description=(ln.get('description') or '').strip(), item_no=(ln.get('sku') or '').strip(),
            mfg_no=(ln.get('part_no') or '').strip(), qty=qty, uom=(ln.get('uom') or 'EA').strip(),
            unit_price=unit, ext_price=ext, arithmetic_ok=ok,
        ))

    total, subtotal, tax = _f(data.get('total')), _f(data.get('subtotal')), _f(data.get('tax'))
    invoice_no = str(data.get('invoice_no') or '').strip()
    is_credit = (total is not None and total < 0) or invoice_no.upper().endswith('CM')
    totals_ok = (subtotal is not None and total is not None
                 and abs((subtotal + (tax or 0)) - total) <= 0.03 * max(1.0, abs(total)))
    return ParsedInvoice(
        invoice_no=invoice_no, vendor_name=_norm_vendor(data.get('vendor_name')),
        invoice_date=_iso(data.get('invoice_date')), po='', job='', status='',
        is_credit=is_credit, subtotal=subtotal, shipping=0.0, tax=tax, total=total,
        lines=lines, totals_ok=totals_ok, raw_block=f'LLM:{Path(pdf_path).name}',
    )


def _reconciles(inv: ParsedInvoice) -> bool:
    if not inv.lines or not all(l.arithmetic_ok for l in inv.lines):
        return False
    line_sum = sum(l.ext_price or 0 for l in inv.lines)
    if inv.subtotal is not None:
        return abs(line_sum - inv.subtotal) <= 0.03 * max(1.0, abs(inv.subtotal))
    if inv.total is not None:
        return abs((line_sum + (inv.tax or 0)) - inv.total) <= 0.03 * max(1.0, abs(inv.total))
    return False


def ingest_invoice_pdfs(session: Session, paths: list, model: str | None = None, log=None) -> dict:
    """Extract + ingest a batch of invoice PDFs. Dedups identical files, skips
    non-invoices, and ingests only invoices whose arithmetic reconciles; the rest
    are counted as flagged (kept in the drop folder for review)."""
    stats = {'files': len(paths), 'dup_file': 0, 'not_invoice': 0, 'flagged_recon': 0,
             'errors': 0, 'ingested': 0, 'lines_priced': 0}
    seen: set = set()
    for i, p in enumerate(paths):
        try:
            b = Path(p).read_bytes()
            h = hashlib.sha256(b).hexdigest()
            if h in seen:
                stats['dup_file'] += 1
                continue
            seen.add(h)
            inv = extract_invoice_pdf(p, model=model)
        except Exception as exc:  # noqa: BLE001 - one bad PDF must not stop the batch
            stats['errors'] += 1
            if log:
                log(f'  ERROR {Path(p).name[:40]}: {type(exc).__name__}: {exc}')
            continue
        if inv is None:
            stats['not_invoice'] += 1
            continue
        if not _reconciles(inv):
            stats['flagged_recon'] += 1
            if log:
                log(f'  FLAG (no reconcile) {inv.vendor_name} {inv.invoice_no} {Path(p).name[:30]}')
            continue
        r = ingest_parsed_invoices(session, [inv], source_slug='invoice')
        stats['ingested'] += 1
        stats['lines_priced'] += r['lines_priced']
        if log and (i % 25 == 0):
            log(f'  ... {i + 1}/{len(paths)} processed; {stats["ingested"]} ingested')
    return stats
