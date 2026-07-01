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
from app.models.tables import ChemicalUsageLog, PoolVessel, Property, ServiceLog, WaterTestLog
from app.services.calibration import compare_estimate_to_actual, save_suggested_calibration
from ui._shared import configure_page, page_header

configure_page('Compare & Train', icon='📊')
page_header('Compare & Train', 'Estimate vs logged actuals: variance and calibration suggestions that feed back into pricing.', icon='📊')

with Session(engine) as session:
    properties = list(session.exec(select(Property)).all())
    if not properties:
        st.info("Create properties first.")
        st.stop()
    prop_map = {f"{p.account_type} :: {p.name} | {p.address_line_1}": p for p in properties}
    prop = prop_map[st.selectbox("Property", list(prop_map.keys()))]
    vessels = list(session.exec(select(PoolVessel).where(PoolVessel.property_id == prop.id)).all())
    vessel = vessels[0] if vessels else None

    with st.form("actual_logs"):
        chem_name = st.text_input("Chemical name", value="liquid_chlorine_12pct_gal")
        chem_qty = st.number_input("Chemical quantity", min_value=0.0, value=0.0)
        chem_unit = st.text_input("Unit", value="gal")
        actual_minutes = st.number_input("Minutes on site actual", min_value=0.0, value=0.0)
        drive_minutes = st.number_input("Drive minutes actual", min_value=0.0, value=0.0)
        fc = st.number_input("Free chlorine ppm", min_value=0.0, value=0.0)
        ph = st.number_input("pH", min_value=0.0, value=0.0)
        submit = st.form_submit_button("Save actual logs")
        if submit:
            if chem_qty > 0:
                session.add(ChemicalUsageLog(property_id=prop.id, vessel_id=vessel.id if vessel else None, chemical_name=chem_name, quantity=chem_qty, unit=chem_unit))
            if actual_minutes > 0 or drive_minutes > 0:
                session.add(ServiceLog(property_id=prop.id, vessel_id=vessel.id if vessel else None, minutes_on_site_actual=actual_minutes, drive_minutes_actual=drive_minutes))
            if fc > 0 or ph > 0:
                session.add(WaterTestLog(property_id=prop.id, vessel_id=vessel.id if vessel else None, free_chlorine_ppm=fc, ph=ph))
            session.commit()
            st.success("Logs saved")

    comparison = compare_estimate_to_actual(session, prop.id, vessel.id if vessel else None)
    if not comparison["estimate_found"]:
        st.warning("No estimate run found yet for this property.")
    else:
        variance_df = pd.DataFrame(comparison["chemical_variance"])
        st.subheader("Chemical variance")
        st.dataframe(variance_df, width='stretch', hide_index=True)
        if not variance_df.empty:
            chosen = st.selectbox("Save suggested chemical multiplier for", variance_df["chemical"].tolist())
            chosen_row = variance_df[variance_df["chemical"] == chosen].iloc[0]
            if st.button("Save suggested calibration"):
                save_suggested_calibration(
                    session,
                    model_family=prop.account_type,
                    property_id=prop.id,
                    vessel_id=vessel.id if vessel else None,
                    chemical_name=chosen,
                    chemical_multiplier=float(chosen_row["suggested_multiplier"]),
                    labor_multiplier=float(comparison["labor_variance"]["suggested_labor_multiplier"]),
                    notes="Saved from compare/train UI",
                )
                st.success("Suggested calibration saved")
        st.subheader("Labor variance")
        st.json(comparison["labor_variance"])
