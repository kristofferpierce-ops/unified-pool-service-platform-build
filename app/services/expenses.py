from __future__ import annotations

from datetime import date

from sqlmodel import Session, select

from app.models.tables import ChemicalProduct, ExpenseItem, ProductPriceHistory


def list_expenses(session: Session) -> list[ExpenseItem]:
    return list(session.exec(select(ExpenseItem).order_by(ExpenseItem.category, ExpenseItem.name)).all())


def annual_overhead_total(session: Session) -> float:
    return sum(item.annual_cost for item in list_expenses(session))


def overhead_per_billable_hour(session: Session, billable_hours_per_year: float, number_of_route_techs: int) -> float:
    annual_hours = max(1.0, billable_hours_per_year * number_of_route_techs)
    return annual_overhead_total(session) / annual_hours


def latest_unit_cost(session: Session, product: ChemicalProduct) -> float:
    latest = session.exec(
        select(ProductPriceHistory)
        .where(ProductPriceHistory.product_id == product.id)
        .order_by(ProductPriceHistory.effective_date.desc(), ProductPriceHistory.id.desc())
    ).first()
    return latest.unit_cost if latest else product.default_unit_cost


def create_price_history(session: Session, *, product_id: int, vendor_name: str, invoice_number: str,
                         unit_cost: float, pack_size: str, confidence: float, approved_by: str,
                         effective_date: date | None = None) -> ProductPriceHistory:
    record = ProductPriceHistory(
        product_id=product_id,
        vendor_name=vendor_name,
        invoice_number=invoice_number,
        effective_date=effective_date or date.today(),
        unit_cost=unit_cost,
        pack_size=pack_size,
        confidence=confidence,
        approved_by=approved_by,
    )
    session.add(record)
    session.commit()
    session.refresh(record)
    return record
