"""Distributor invoice import: portal-text -> priced product ledger.

First adapter: Heritage Pool Supply's online "Invoice History" copy-paste (one
paste = many invoices). Deterministic, so it backfills historical invoices with
no API key. The LLM general-extractor (for other vendors / PDFs / format drift)
plugs in later behind the same ParsedInvoice contract.

Design decisions (owner-confirmed 2026-08-01):
  * The manufacturer part number (MFG #) is the cross-vendor product key -- a
    Jandy FHPM1.0 is the same product whether Heritage or Key West Chemical sells
    it, so prices become comparable.
  * Credit memos / returns (invoice # ...CM, or negative qty/price) are RECORDED
    but EXCLUDED from the price ledger -- a -$1,900 pump is a return, not a deal.
  * ChemicalProduct is reused as the general product catalog, keyed on MFG #.
  * Anchored on stable markers (Invoice #, ITEM #/MFG #, Invoice Summary, $x /UOM),
    not exact spacing, so minor format drift is tolerated; a line that will not
    parse is flagged, never silently dropped.
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from datetime import date, datetime

from sqlmodel import Session, select

from app.models.tables import ChemicalProduct, InvoiceDocument, ProductPriceHistory
from app.services.expenses import create_price_history
from app.services.vendor_matching import resolve_vendor

_ITEM_MFG = re.compile(r'^ITEM # (\S+)(?:\s+MFG # (\S*))?', re.I)
_HEADER_END = 'Reorder Qty'
_SKIP_LINES = {'Qty', 'Reorder Qty', 'Documents:', 'Product Description', 'UOM',
               'Unit Price', 'Ext. Price', 'Add selected to Shopping List'}


@dataclass
class ParsedLine:
    description: str
    item_no: str          # distributor SKU
    mfg_no: str           # manufacturer part number (cross-vendor key); '' if none/0
    qty: float | None
    uom: str
    unit_price: float | None
    ext_price: float | None
    arithmetic_ok: bool   # qty * unit == ext within tolerance


@dataclass
class ParsedInvoice:
    invoice_no: str
    vendor_name: str
    invoice_date: date | None
    po: str
    job: str
    status: str
    is_credit: bool       # credit memo / return -> excluded from pricing
    subtotal: float | None
    shipping: float | None
    tax: float | None
    total: float | None
    lines: list = field(default_factory=list)   # list[ParsedLine]
    totals_ok: bool = True                       # subtotal + shipping + tax == total
    raw_block: str = ''


def _money(s: str) -> float | None:
    if s is None:
        return None
    m = re.search(r'[\d,]+\.\d+|\d+', s)
    if not m:
        return None
    val = float(m.group(0).replace(',', ''))
    return -val if s.strip().startswith('-') or s.strip().startswith('(') else val


def _num(s: str) -> float | None:
    m = re.search(r'-?\d+(?:\.\d+)?', s or '')
    return float(m.group(0)) if m else None


def _clean_lines(block: str) -> list:
    return [ln.strip() for ln in block.replace('\t', '\n').split('\n') if ln.strip()]


def _parse_date(block: str) -> date | None:
    m = re.search(r'Invoice Date:\s*(\d{1,2}/\d{1,2}/\d{2,4})', block)
    if not m:
        return None
    raw = m.group(1)
    for fmt in ('%m/%d/%y', '%m/%d/%Y'):
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    return None


def _value_after(clean: list, label: str) -> float | None:
    for i, ln in enumerate(clean):
        if ln == label and i + 1 < len(clean):
            return _money(clean[i + 1])
    return None


def _parse_lines(clean: list) -> list:
    try:
        start = clean.index(_HEADER_END) + 1
    except ValueError:
        return []
    try:
        end = clean.index('Invoice Summary', start)
    except ValueError:
        end = len(clean)

    lines: list = []
    desc_buffer: list = []
    i = start
    while i < end:
        ln = clean[i]
        m = _ITEM_MFG.match(ln)
        if m:
            item_no = m.group(1)
            mfg_no = (m.group(2) or '').strip()
            if mfg_no in ('0', ''):
                mfg_no = ''
            description = ' '.join(desc_buffer).strip()
            desc_buffer = []
            # next 4 value tokens: qty, uom, unit ($x /UOM), ext ($y)
            vals: list = []
            j = i + 1
            while j < end and len(vals) < 4:
                v = clean[j]
                if v in _SKIP_LINES:
                    j += 1
                    continue
                vals.append(v)
                j += 1
            vals += [''] * (4 - len(vals))
            qty, uom, unit, ext = _num(vals[0]), vals[1], _money(vals[2]), _money(vals[3])
            ok = (qty is not None and unit is not None and ext is not None
                  and abs(qty * unit - ext) <= 0.02 * max(1.0, abs(ext)))
            lines.append(ParsedLine(description or item_no, item_no, mfg_no, qty,
                                    uom, unit, ext, ok))
            i = j
        else:
            if ln not in _SKIP_LINES:
                desc_buffer.append(ln)
            i += 1
    return lines


def parse_heritage_paste(text: str) -> list:
    """Split a Heritage 'Invoice History' paste into structured invoices."""
    invoices: list = []
    for block in re.split(r'(?=Invoice # \S)', text):
        if 'Invoice #' not in block:
            continue
        m = re.search(r'Invoice # (\S+)', block)
        if not m:
            continue
        invoice_no = m.group(1).strip()
        clean = _clean_lines(block)
        po = (re.search(r'PO #:\s*(.+)', block) or [None, ''])
        po = po.group(1).strip() if hasattr(po, 'group') else ''
        job_m = re.search(r'Job Name:\s*(.+)', block)
        status_m = re.search(r'Invoice Status:\s*(\w+)', block)
        lines = _parse_lines(clean)
        subtotal = _value_after(clean, 'Subtotal')
        shipping = _value_after(clean, 'Shipping & Charges')
        tax = _value_after(clean, 'Tax Total')
        total = _value_after(clean, 'Total')
        is_credit = invoice_no.upper().endswith('CM') or (total is not None and total < 0)
        totals_ok = (subtotal is not None and total is not None
                     and abs((subtotal + (shipping or 0) + (tax or 0)) - total) <= 0.02 * max(1.0, abs(total)))
        invoices.append(ParsedInvoice(
            invoice_no=invoice_no,
            vendor_name='Heritage Pool Supply',
            invoice_date=_parse_date(block),
            po=po,
            job=job_m.group(1).strip() if job_m else '',
            status=status_m.group(1) if status_m else '',
            is_credit=is_credit,
            subtotal=subtotal, shipping=shipping, tax=tax, total=total,
            lines=lines, totals_ok=totals_ok, raw_block=block.strip(),
        ))
    return invoices


def _infer_family(description: str) -> str:
    d = description.lower()
    checks = [('pump', 'pump'), ('filter', 'filter'), ('grid', 'filter'), ('valve', 'valve'),
              ('light', 'light'), ('heat', 'heater'), ('sensor', 'controller'), ('controller', 'controller'),
              ('motor', 'motor'), ('reagent', 'chemical'), ('test kit', 'chemical'), (' dpd', 'chemical'),
              ('chlor', 'chemical'), ('salt', 'chemical'),
              ('pipe', 'plumbing'), ('elbow', 'plumbing'), ('tee', 'plumbing'), ('coupling', 'plumbing'),
              ('bushing', 'plumbing'), ('pvc', 'plumbing')]
    for kw, fam in checks:
        if kw in d:
            return fam
    return 'equipment'


def resolve_product_by_mfg(session: Session, *, mfg_no: str, item_no: str, description: str, uom: str):
    """Find or create the canonical product, keyed on manufacturer part number
    (falling back to the distributor SKU when MFG # is absent)."""
    product = None
    if mfg_no:
        product = session.exec(
            select(ChemicalProduct).where(ChemicalProduct.manufacturer_part_number == mfg_no)
        ).first()
    if not product and item_no:
        product = session.exec(select(ChemicalProduct).where(ChemicalProduct.sku == item_no)).first()
    if product:
        return product, False
    product = ChemicalProduct(
        sku=item_no or mfg_no or (description[:40] or 'unknown'),
        name=description[:200] or (mfg_no or item_no),
        unit=(uom or 'EA'),
        manufacturer_part_number=mfg_no,
        default_vendor='Heritage Pool Supply',
        product_family=_infer_family(description),
    )
    session.add(product)
    session.commit()
    session.refresh(product)
    return product, True


def ingest_parsed_invoices(session: Session, invoices: list, source_slug: str = 'heritage') -> dict:
    """Load parsed invoices into the vendor + product + price ledger. Idempotent
    per (vendor, invoice #). Credit memos are recorded but not priced."""
    vres = resolve_vendor(session, source=source_slug, external_id='heritage-pool-supply',
                          name='Heritage Pool Supply', vendor_type='distributor')
    vendor_id = vres.vendor_id

    summary = {'invoices_imported': 0, 'invoices_skipped_dup': 0, 'credit_memos': 0,
               'lines_priced': 0, 'lines_excluded_credit': 0, 'products_created': 0, 'products_matched': 0}

    for inv in invoices:
        existing = session.exec(
            select(InvoiceDocument).where(
                InvoiceDocument.vendor_name == inv.vendor_name,
                InvoiceDocument.invoice_number == inv.invoice_no,
            )
        ).first()
        if existing:
            summary['invoices_skipped_dup'] += 1
            continue

        doc = InvoiceDocument(
            vendor_name=inv.vendor_name,
            original_filename='heritage_paste',
            file_path='',
            document_hash=hashlib.sha256(inv.raw_block.encode('utf-8')).hexdigest(),
            invoice_number=inv.invoice_no,
            extracted_text=inv.raw_block,
            parser_name='heritage_paste_parser',
            status='imported',
        )
        session.add(doc)
        session.commit()
        summary['invoices_imported'] += 1
        if inv.is_credit:
            summary['credit_memos'] += 1

        for ln in inv.lines:
            product, created = resolve_product_by_mfg(
                session, mfg_no=ln.mfg_no, item_no=ln.item_no, description=ln.description, uom=ln.uom)
            summary['products_created' if created else 'products_matched'] += 1

            # Record but do not price credit memos / negatives / zero-cost lines.
            if inv.is_credit or (ln.qty or 0) < 0 or (ln.unit_price or 0) <= 0:
                summary['lines_excluded_credit'] += 1
                continue

            ph = create_price_history(
                session, product_id=product.id, vendor_name=inv.vendor_name,
                invoice_number=inv.invoice_no, unit_cost=ln.unit_price, pack_size=ln.uom,
                confidence=1.0 if ln.arithmetic_ok else 0.5, approved_by='heritage_import',
                effective_date=inv.invoice_date,
            )
            ph.vendor_id = vendor_id
            session.add(ph)
            session.commit()
            summary['lines_priced'] += 1

    return summary
