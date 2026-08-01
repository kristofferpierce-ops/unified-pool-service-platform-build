"""Cross-vendor search over the invoice + price ledger.

Search an item (name / description / part # / SKU) or an invoice number and get
everything relevant across ALL vendors -- so a Jandy pump bought from Heritage
and from another distributor both surface, each with its own price, vendor, date,
and invoice number. This is a read-only view over ProductPriceHistory +
InvoiceDocument; it needs no external service.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from sqlmodel import Session, select

from app.models.tables import ChemicalProduct, InvoiceDocument, ProductPriceHistory


@dataclass
class PricePoint:
    vendor: str
    unit_cost: float
    pack_size: str
    effective_date: object
    invoice_no: str


@dataclass
class ProductHit:
    product_id: int
    sku: str
    name: str
    mfg_no: str
    product_family: str
    points: list = field(default_factory=list)   # PricePoint, chronological
    vendors: list = field(default_factory=list)   # distinct vendor names
    best_vendor: str = ''
    best_cost: float = 0.0
    spread_pct: float = 0.0                        # (worst-best)/best across vendors' latest cost


@dataclass
class InvoiceHit:
    invoice_no: str
    vendor: str
    line_count: int
    total_cost: float
    lines: list = field(default_factory=list)      # (name, unit_cost, pack_size)


def _matches(hay: str, q: str) -> bool:
    return q in (hay or '').lower()


def _build_product_hit(session: Session, p: ChemicalProduct) -> ProductHit:
    rows = session.exec(
        select(ProductPriceHistory)
        .where(ProductPriceHistory.product_id == p.id)
        .order_by(ProductPriceHistory.effective_date, ProductPriceHistory.id)
    ).all()
    points = [PricePoint(r.vendor_name or '(unknown)', r.unit_cost, r.pack_size, r.effective_date, r.invoice_number)
              for r in rows]
    # latest cost per vendor -> the comparison
    latest: dict = {}
    for r in rows:
        latest[r.vendor_name or '(unknown)'] = r.unit_cost
    best_vendor, best_cost, spread = '', 0.0, 0.0
    if latest:
        ordered = sorted(latest.items(), key=lambda kv: kv[1])
        best_vendor, best_cost = ordered[0]
        worst = ordered[-1][1]
        spread = ((worst - best_cost) / best_cost * 100.0) if best_cost else 0.0
    return ProductHit(
        product_id=p.id, sku=p.sku, name=p.name, mfg_no=p.manufacturer_part_number,
        product_family=p.product_family, points=points, vendors=sorted(latest.keys()),
        best_vendor=best_vendor, best_cost=best_cost, spread_pct=spread,
    )


def search_ledger(session: Session, query: str, limit: int = 50) -> dict:
    """Return {'products': [ProductHit], 'invoices': [InvoiceHit]} for a query that
    matches a product (name/SKU/MFG #) or an invoice number (partial ok)."""
    q = (query or '').strip().lower()
    products: list = []
    invoices: list = []
    if not q:
        return {'products': products, 'invoices': invoices}

    for p in session.exec(select(ChemicalProduct)).all():
        hay = ' '.join([p.name or '', p.sku or '', p.manufacturer_part_number or ''])
        if _matches(hay, q):
            products.append(_build_product_hit(session, p))
    # most-comparable first: more vendors, then wider spread
    products.sort(key=lambda h: (-len(h.vendors), -h.spread_pct, h.name))

    seen: set = set()
    for d in session.exec(select(InvoiceDocument)).all():
        if not _matches(d.invoice_number, q) or d.invoice_number in seen:
            continue
        seen.add(d.invoice_number)
        rows = session.exec(
            select(ProductPriceHistory).where(ProductPriceHistory.invoice_number == d.invoice_number)
        ).all()
        by_id = {r.product_id: r for r in rows}
        names = {pr.id: pr.name for pr in session.exec(
            select(ChemicalProduct).where(ChemicalProduct.id.in_(list(by_id.keys())))
        ).all()} if by_id else {}
        lines = [(names.get(r.product_id, f'product {r.product_id}'), r.unit_cost, r.pack_size) for r in rows]
        invoices.append(InvoiceHit(
            invoice_no=d.invoice_number, vendor=d.vendor_name, line_count=len(lines),
            total_cost=round(sum(r.unit_cost for r in rows), 2), lines=lines,
        ))

    return {'products': products[:limit], 'invoices': invoices[:limit]}
