from __future__ import annotations

import sys
from datetime import UTC, datetime
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st
from sqlmodel import Session, select

from app.core.database import engine
from app.models.tables import CommercialDelivery, CommercialVendorOrder, Property
from app.services.commercial import add_delivery_item, add_vendor_order_item, create_delivery, create_vendor_order, direct_delivery_report_dataframe, export_direct_delivery_report_xlsx
from ui._shared import configure_page, page_header

configure_page('Commercial Deliveries', icon='🚚')
page_header('Commercial Deliveries', 'Monthly delivery and property-level billing review for commercial accounts.', icon='🚚')

with Session(engine) as session:
    properties = list(session.exec(select(Property).where(Property.account_type == "commercial")).all())
    prop_map = {f"{p.name} | {p.address_line_1}": p.id for p in properties}

    st.subheader("Create commercial vendor order")
    if properties:
        with st.form("vendor_order"):
            property_label = st.selectbox("Property", list(prop_map.keys()))
            vendor_name = st.text_input("Vendor name")
            order_number = st.text_input("Order number")
            notes = st.text_area("Notes")
            submit_order = st.form_submit_button("Create order")
            if submit_order and vendor_name and order_number:
                order = create_vendor_order(session, prop_map[property_label], vendor_name, order_number, notes)
                st.success(f"Order created: {order.order_number}")

    orders = list(session.exec(select(CommercialVendorOrder).order_by(CommercialVendorOrder.ordered_at.desc())).all())
    if orders:
        order_map = {f"{o.order_number} | {o.vendor_name}": o.id for o in orders}
        with st.form("add_order_item"):
            order_label = st.selectbox("Order", list(order_map.keys()))
            product_name = st.text_input("Product name")
            quantity_ordered = st.number_input("Quantity ordered", min_value=0.0, value=55.0)
            unit = st.text_input("Unit", value="gal")
            unit_cost = st.number_input("Unit cost", min_value=0.0, value=0.0)
            submit_item = st.form_submit_button("Add order item")
            if submit_item and product_name:
                add_vendor_order_item(session, order_map[order_label], product_name, quantity_ordered, unit, unit_cost)
                st.success("Order item added")

    st.subheader("Log delivered chemicals")
    if properties:
        with st.form("create_delivery"):
            property_label = st.selectbox("Delivery property", list(prop_map.keys()))
            vendor_name = st.text_input("Delivery vendor")
            invoice_number = st.text_input("Invoice number")
            delivery_ticket = st.text_input("Delivery ticket")
            status = st.selectbox("Status", ["delivered", "confirmed", "discrepancy", "billed"])
            submit_delivery = st.form_submit_button("Create delivery")
            if submit_delivery and vendor_name:
                delivery = create_delivery(session, prop_map[property_label], vendor_name, invoice_number, delivery_ticket, status)
                st.success(f"Delivery created: {delivery.id}")

    deliveries = list(session.exec(select(CommercialDelivery).order_by(CommercialDelivery.delivered_at.desc())).all())
    if deliveries:
        delivery_map = {f"{d.id} | {d.invoice_number} | {d.vendor_name}": d.id for d in deliveries}
        with st.form("add_delivery_item"):
            delivery_label = st.selectbox("Delivery", list(delivery_map.keys()))
            product_name = st.text_input("Delivered product name")
            qty_ordered = st.number_input("Qty ordered", min_value=0.0, value=55.0)
            qty_delivered = st.number_input("Qty delivered", min_value=0.0, value=55.0)
            qty_confirmed = st.number_input("Qty confirmed", min_value=0.0, value=0.0)
            unit = st.text_input("Delivered unit", value="gal")
            unit_cost = st.number_input("Delivered unit cost", min_value=0.0, value=0.0)
            submit_delivery_item = st.form_submit_button("Add delivery item")
            if submit_delivery_item and product_name:
                add_delivery_item(session, delivery_map[delivery_label], product_name, qty_ordered, qty_delivered, qty_confirmed, unit, unit_cost)
                st.success("Delivery item added")

    st.subheader("Monthly direct-delivery report")
    start_date = st.date_input("Start date", value=(datetime.now(UTC).date().replace(day=1)))
    end_date = st.date_input("End date", value=datetime.now(UTC).date())
    report_df = direct_delivery_report_dataframe(session, datetime.combine(start_date, datetime.min.time()), datetime.combine(end_date, datetime.max.time()))
    st.dataframe(report_df, width='stretch', hide_index=True)
    if st.button("Export report to Excel"):
        path = export_direct_delivery_report_xlsx(session, datetime.combine(start_date, datetime.min.time()), datetime.combine(end_date, datetime.max.time()))
        st.success(f"Exported: {path}")
