from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd
from sqlmodel import Session, select

from app.core.config import EXPORT_DIR
from app.models.tables import CommercialDelivery, CommercialDeliveryItem, CommercialVendorOrder, CommercialVendorOrderItem, Property


def create_vendor_order(session: Session, property_id: int, vendor_name: str, order_number: str, notes: str = "") -> CommercialVendorOrder:
    order = CommercialVendorOrder(property_id=property_id, vendor_name=vendor_name, order_number=order_number, notes=notes)
    session.add(order)
    session.commit()
    session.refresh(order)
    return order


def add_vendor_order_item(session: Session, order_id: int, product_name: str, quantity_ordered: float, unit: str,
                          unit_cost: float = 0.0, product_id: int | None = None) -> CommercialVendorOrderItem:
    item = CommercialVendorOrderItem(
        order_id=order_id,
        product_id=product_id,
        product_name=product_name,
        quantity_ordered=quantity_ordered,
        unit=unit,
        unit_cost=unit_cost,
        expected_total=quantity_ordered * unit_cost,
    )
    session.add(item)
    session.commit()
    session.refresh(item)
    return item


def create_delivery(session: Session, property_id: int, vendor_name: str, invoice_number: str,
                    delivery_ticket: str = "", status: str = "delivered", source_document_id: int | None = None,
                    notes: str = "") -> CommercialDelivery:
    delivery = CommercialDelivery(
        property_id=property_id,
        vendor_name=vendor_name,
        invoice_number=invoice_number,
        delivery_ticket=delivery_ticket,
        status=status,
        source_document_id=source_document_id,
        notes=notes,
    )
    session.add(delivery)
    session.commit()
    session.refresh(delivery)
    return delivery


def add_delivery_item(session: Session, delivery_id: int, product_name: str, quantity_ordered: float,
                      quantity_delivered: float, quantity_confirmed: float, unit: str, unit_cost: float,
                      product_id: int | None = None, order_item_id: int | None = None, confidence: float = 0.0) -> CommercialDeliveryItem:
    item = CommercialDeliveryItem(
        delivery_id=delivery_id,
        order_item_id=order_item_id,
        product_id=product_id,
        product_name=product_name,
        quantity_ordered=quantity_ordered,
        quantity_delivered=quantity_delivered,
        quantity_confirmed=quantity_confirmed,
        unit=unit,
        unit_cost=unit_cost,
        confidence=confidence,
    )
    session.add(item)
    session.commit()
    session.refresh(item)
    return item


def direct_delivery_report_dataframe(session: Session, start_dt: datetime, end_dt: datetime) -> pd.DataFrame:
    deliveries = list(session.exec(
        select(CommercialDelivery)
        .where(CommercialDelivery.delivered_at >= start_dt, CommercialDelivery.delivered_at <= end_dt)
        .order_by(CommercialDelivery.delivered_at, CommercialDelivery.id)
    ).all())
    rows = []
    for delivery in deliveries:
        property_row = session.get(Property, delivery.property_id)
        items = list(session.exec(select(CommercialDeliveryItem).where(CommercialDeliveryItem.delivery_id == delivery.id)).all())
        for item in items:
            rows.append({
                "Property": property_row.name if property_row else f"Property {delivery.property_id}",
                "Date": delivery.delivered_at.date().isoformat(),
                "Vendor": delivery.vendor_name,
                "Invoice Number": delivery.invoice_number,
                "Delivery Ticket": delivery.delivery_ticket,
                "Product": item.product_name,
                "Qty Ordered": item.quantity_ordered,
                "Qty Delivered": item.quantity_delivered,
                "Qty Confirmed": item.quantity_confirmed,
                "Unit": item.unit,
                "Unit Cost": item.unit_cost,
                "Extended Cost": item.quantity_delivered * item.unit_cost,
                "Variance": item.quantity_delivered - item.quantity_ordered,
                "Status": delivery.status,
            })
    return pd.DataFrame(rows)


def export_direct_delivery_report_xlsx(session: Session, start_dt: datetime, end_dt: datetime) -> Path:
    df = direct_delivery_report_dataframe(session, start_dt, end_dt)
    filename = EXPORT_DIR / f"direct_delivery_report_{start_dt.date()}_{end_dt.date()}.xlsx"
    with pd.ExcelWriter(filename, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="Direct Deliveries", index=False)
        if not df.empty:
            summary = df.groupby("Property", as_index=False)["Extended Cost"].sum().rename(columns={"Extended Cost": "Property Total"})
            summary.to_excel(writer, sheet_name="Property Summary", index=False)
    return filename
