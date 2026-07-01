"""Purchasing intelligence over the product price-history ledger.

Turns the ProductPriceHistory ledger (fed by invoice ingestion + manual entry)
into decisions:
  - a supplier price book per product,
  - best-source recommendation (cheapest current vendor + the spread you're
    leaving on the table),
  - price anomaly flags (a vendor's latest cost jumped vs its previous one).

No new tables: a "supplier" is just a distinct vendor_name on the ledger. This
is pure analytics over what invoices already record, so it works the moment any
price history exists.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from sqlmodel import Session, select

from app.models.tables import ChemicalProduct, ProductPriceHistory


@dataclass
class VendorPrice:
    vendor: str
    unit_cost: float
    effective_date: date
    pack_size: str
    observations: int  # how many ledger rows back this vendor for this product


@dataclass
class BestSource:
    product_id: int
    sku: str
    name: str
    unit: str
    vendors: list  # list[VendorPrice], cheapest first
    best_vendor: str
    best_unit_cost: float
    worst_unit_cost: float
    spread_abs: float          # worst - best, per unit
    spread_pct: float          # spread relative to best
    baseline_unit_cost: float  # the product's default_unit_cost, for reference


@dataclass
class PriceAnomaly:
    product_id: int
    sku: str
    name: str
    vendor: str
    previous_cost: float
    latest_cost: float
    change_pct: float
    direction: str  # 'up' | 'down'
    effective_date: date


def list_products(session: Session, active_only: bool = True) -> list[ChemicalProduct]:
    stmt = select(ChemicalProduct).order_by(ChemicalProduct.name)
    products = list(session.exec(stmt).all())
    if active_only:
        products = [p for p in products if p.is_active]
    return products


def _history_for(session: Session, product_id: int) -> list[ProductPriceHistory]:
    return list(session.exec(
        select(ProductPriceHistory)
        .where(ProductPriceHistory.product_id == product_id)
        .order_by(ProductPriceHistory.effective_date, ProductPriceHistory.id)
    ).all())


def _latest_by_vendor(history: list[ProductPriceHistory]) -> list[VendorPrice]:
    """Most-recent observation per vendor, cheapest first."""
    by_vendor: dict[str, list[ProductPriceHistory]] = {}
    for row in history:
        by_vendor.setdefault(row.vendor_name or '(unknown)', []).append(row)

    prices: list[VendorPrice] = []
    for vendor, rows in by_vendor.items():
        rows.sort(key=lambda r: (r.effective_date, r.id or 0))
        latest = rows[-1]
        prices.append(VendorPrice(
            vendor=vendor,
            unit_cost=latest.unit_cost,
            effective_date=latest.effective_date,
            pack_size=latest.pack_size,
            observations=len(rows),
        ))
    prices.sort(key=lambda p: p.unit_cost)
    return prices


def best_source_for_product(session: Session, product: ChemicalProduct) -> BestSource | None:
    """Best current supplier for one product, or None if it has no price history."""
    history = _history_for(session, product.id)
    vendors = _latest_by_vendor(history)
    if not vendors:
        return None
    best = vendors[0]
    worst = vendors[-1]
    spread_abs = worst.unit_cost - best.unit_cost
    spread_pct = (spread_abs / best.unit_cost * 100.0) if best.unit_cost else 0.0
    return BestSource(
        product_id=product.id,
        sku=product.sku,
        name=product.name,
        unit=product.unit,
        vendors=vendors,
        best_vendor=best.vendor,
        best_unit_cost=best.unit_cost,
        worst_unit_cost=worst.unit_cost,
        spread_abs=spread_abs,
        spread_pct=spread_pct,
        baseline_unit_cost=product.default_unit_cost,
    )


def purchasing_overview(session: Session) -> list[BestSource]:
    """Best-source rows for every product that has any price history."""
    rows: list[BestSource] = []
    for product in list_products(session):
        bs = best_source_for_product(session, product)
        if bs is not None:
            rows.append(bs)
    return rows


def detect_price_anomalies(session: Session, threshold_pct: float = 15.0) -> list[PriceAnomaly]:
    """Flag where a vendor's latest cost moved > threshold% vs its previous one.

    Compares consecutive observations for the same (product, vendor) so a jump
    is measured against that vendor's own prior price, not a cross-vendor blend.
    """
    anomalies: list[PriceAnomaly] = []
    for product in list_products(session):
        history = _history_for(session, product.id)
        by_vendor: dict[str, list[ProductPriceHistory]] = {}
        for row in history:
            by_vendor.setdefault(row.vendor_name or '(unknown)', []).append(row)
        for vendor, rows in by_vendor.items():
            if len(rows) < 2:
                continue
            rows.sort(key=lambda r: (r.effective_date, r.id or 0))
            prev, latest = rows[-2], rows[-1]
            if prev.unit_cost <= 0:
                continue
            change_pct = (latest.unit_cost - prev.unit_cost) / prev.unit_cost * 100.0
            if abs(change_pct) >= threshold_pct:
                anomalies.append(PriceAnomaly(
                    product_id=product.id,
                    sku=product.sku,
                    name=product.name,
                    vendor=vendor,
                    previous_cost=prev.unit_cost,
                    latest_cost=latest.unit_cost,
                    change_pct=change_pct,
                    direction='up' if change_pct > 0 else 'down',
                    effective_date=latest.effective_date,
                ))
    anomalies.sort(key=lambda a: abs(a.change_pct), reverse=True)
    return anomalies


@dataclass
class PurchasingSummary:
    products_tracked: int
    suppliers_seen: int
    multi_supplier_products: int
    anomalies: int
    total_spread_per_unit: float  # sum over products of (worst-best) per unit
    overview: list = field(default_factory=list)   # list[BestSource]
    anomaly_list: list = field(default_factory=list)  # list[PriceAnomaly]


def purchasing_summary(session: Session, threshold_pct: float = 15.0) -> PurchasingSummary:
    overview = purchasing_overview(session)
    anomalies = detect_price_anomalies(session, threshold_pct=threshold_pct)
    suppliers: set[str] = set()
    for bs in overview:
        suppliers.update(v.vendor for v in bs.vendors)
    return PurchasingSummary(
        products_tracked=len(overview),
        suppliers_seen=len(suppliers),
        multi_supplier_products=sum(1 for bs in overview if len(bs.vendors) > 1),
        anomalies=len(anomalies),
        total_spread_per_unit=sum(bs.spread_abs for bs in overview),
        overview=overview,
        anomaly_list=anomalies,
    )
