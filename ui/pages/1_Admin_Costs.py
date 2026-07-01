from __future__ import annotations

import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd
import streamlit as st
from sqlmodel import Session, select

from app.core.database import engine
from app.models.tables import ChemicalProduct, ExpenseItem, ProductPriceHistory
from ui._shared import configure_page, page_header

configure_page('Admin Costs', icon='🧾')
page_header('Admin Costs', 'Shared overhead and chemical-product costs that feed estimating and the true cost per hour.', icon='🧾')

with Session(engine) as session:
    expense_rows = list(session.exec(select(ExpenseItem).order_by(ExpenseItem.category, ExpenseItem.name)).all())
    expense_df = pd.DataFrame([
        {"id": row.id, "Category": row.category, "Name": row.name, "Annual Cost": row.annual_cost, "Notes": row.notes}
        for row in expense_rows
    ])
    edited = st.data_editor(expense_df, width='stretch', hide_index=True, num_rows="dynamic")
    if st.button("Save expense changes", type="primary"):
        for _, r in edited.iterrows():
            if pd.isna(r.get("id")):
                session.add(ExpenseItem(category=str(r["Category"]), name=str(r["Name"]), annual_cost=float(r["Annual Cost"]), notes=str(r.get("Notes") or "")))
            else:
                item = session.get(ExpenseItem, int(r["id"]))
                if item:
                    item.category = str(r["Category"])
                    item.name = str(r["Name"])
                    item.annual_cost = float(r["Annual Cost"])
                    item.notes = str(r.get("Notes") or "")
        session.commit()
        st.success("Expenses saved")

    st.subheader("Chemical products and default costs")
    product_rows = list(session.exec(select(ChemicalProduct).order_by(ChemicalProduct.name)).all())
    product_df = pd.DataFrame([
        {
            "id": row.id,
            "SKU": row.sku,
            "Name": row.name,
            "Unit": row.unit,
            "Default Unit Cost": row.default_unit_cost,
            "Manufacturer": row.manufacturer,
            "Part Number": row.manufacturer_part_number,
            "Aliases CSV": row.aliases_csv,
        }
        for row in product_rows
    ])
    edited_products = st.data_editor(product_df, width='stretch', hide_index=True, num_rows="dynamic")
    if st.button("Save product changes"):
        for _, r in edited_products.iterrows():
            if pd.isna(r.get("id")):
                session.add(ChemicalProduct(
                    sku=str(r["SKU"]), name=str(r["Name"]), unit=str(r["Unit"]),
                    default_unit_cost=float(r["Default Unit Cost"]), manufacturer=str(r.get("Manufacturer") or ""),
                    manufacturer_part_number=str(r.get("Part Number") or ""), aliases_csv=str(r.get("Aliases CSV") or ""),
                ))
            else:
                item = session.get(ChemicalProduct, int(r["id"]))
                if item:
                    item.sku = str(r["SKU"])
                    item.name = str(r["Name"])
                    item.unit = str(r["Unit"])
                    item.default_unit_cost = float(r["Default Unit Cost"])
                    item.manufacturer = str(r.get("Manufacturer") or "")
                    item.manufacturer_part_number = str(r.get("Part Number") or "")
                    item.aliases_csv = str(r.get("Aliases CSV") or "")
        session.commit()
        st.success("Products saved")

    st.subheader("Recent price history")
    history_rows = list(session.exec(select(ProductPriceHistory).order_by(ProductPriceHistory.effective_date.desc(), ProductPriceHistory.id.desc())).all())
    hist_df = pd.DataFrame([row.model_dump() for row in history_rows]) if history_rows else pd.DataFrame()
    st.dataframe(hist_df, width='stretch', hide_index=True)
