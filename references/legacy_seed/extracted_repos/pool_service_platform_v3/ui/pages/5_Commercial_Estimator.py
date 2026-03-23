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
from app.models.tables import EquipmentAsset, EstimateScenario, PoolVessel, Property
from app.services.baseline import get_active_model
from app.services.estimator import EstimateInput, calculate_estimate, save_estimate_run

st.title("Commercial Estimator")

with Session(engine) as session:
    properties = list(session.exec(select(Property).where(Property.account_type == "commercial")).all())
    if not properties:
        st.info("Create a commercial property first on the Accounts & Properties page.")
        st.stop()
    prop_map = {f"{p.name} | {p.address_line_1}": p for p in properties}
    prop = prop_map[st.selectbox("Commercial property", list(prop_map.keys()))]
    vessels = list(session.exec(select(PoolVessel).where(PoolVessel.property_id == prop.id)).all())
    vessel_map = {f"{v.id} :: {v.name}": v for v in vessels}
    vessel = vessel_map[st.selectbox("Vessel", list(vessel_map.keys()))]
    assets = list(session.exec(select(EquipmentAsset).where(EquipmentAsset.vessel_id == vessel.id)).all())

    cols = st.columns(3)
    gallons = cols[0].number_input("Gallons", min_value=0.0, value=vessel.gallons)
    visits_per_month = cols[1].number_input("Visits per month", min_value=1.0, value=vessel.service_frequency_per_month)
    minutes_on_site = cols[2].number_input("Minutes on site", min_value=0.0, value=vessel.minutes_on_site)
    cols = st.columns(4)
    drive_minutes = cols[0].number_input("Drive minutes round trip", min_value=0.0, value=prop.drive_minutes_round_trip)
    techs_on_visit = cols[1].number_input("Techs on visit", min_value=1, value=1)
    training_weeks = cols[2].number_input("Training / peak weeks per year", min_value=0, value=vessel.training_weeks_per_year)
    target_margin = cols[3].number_input("Target margin %", min_value=0.0, value=35.0)
    cols = st.columns(6)
    bath = cols[0].slider("Bath", 1, 10, vessel.bathing_score)
    debris = cols[1].slider("Debris", 1, 10, vessel.debris_score)
    filtration = cols[2].slider("Filtration", 1, 10, vessel.filtration_score)
    overflow = cols[3].slider("Overflow", 1, 10, vessel.overflow_score)
    backwash = cols[4].slider("Backwash", 1, 10, vessel.backwash_score)
    global_adj = cols[5].number_input("Global adj %", value=0.0)

    scenario_name = st.text_input("Scenario name", value="baseline commercial quote")

    if st.button("Run commercial estimate", type="primary"):
        model = get_active_model(session, "commercial")
        scenario = EstimateScenario(
            property_id=prop.id,
            vessel_id=vessel.id,
            scenario_name=scenario_name,
            model_family="commercial",
            baseline_model_version_id=model.id,
            target_margin_pct=target_margin,
            global_adjustment_pct=global_adj,
            notes=f"Peak weeks: {training_weeks}",
        )
        session.add(scenario)
        session.commit()
        session.refresh(scenario)
        estimate_input = EstimateInput(
            property_id=prop.id, vessel_id=vessel.id, model_family="commercial", gallons=gallons,
            visits_per_month=visits_per_month, minutes_on_site=minutes_on_site,
            drive_minutes_round_trip=drive_minutes, techs_on_visit=techs_on_visit,
            bath_score=bath, debris_score=debris, filtration_score=filtration,
            overflow_score=overflow, backwash_score=backwash,
            target_margin_pct=target_margin, global_adjustment_pct=global_adj,
        )
        output = calculate_estimate(session, estimate_input)
        save_estimate_run(session, scenario.id, estimate_input, output)
        m1, m2, m3 = st.columns(3)
        m1.metric("Monthly real cost", f"${output.monthly_real_cost:,.2f}")
        m2.metric("Monthly sell price", f"${output.monthly_sell_price:,.2f}")
        m3.metric("Annual real cost", f"${output.annual_real_cost:,.2f}")
        chem_df = pd.DataFrame([
            {
                "Chemical": k,
                "Annual Qty": v["annual_quantity"],
                "Monthly Qty": v["monthly_quantity"],
                "Annual Cost": output.chemical_costs[k]["annual_cost"],
            }
            for k, v in output.chemical_quantities.items()
        ])
        st.dataframe(chem_df, use_container_width=True, hide_index=True)

    st.subheader("Equipment assets for selected vessel")
    st.dataframe(pd.DataFrame([row.model_dump() for row in assets]), use_container_width=True, hide_index=True)

    with st.form("add_equipment"):
        asset_type = st.text_input("Asset type")
        manufacturer = st.text_input("Manufacturer")
        model_number = st.text_input("Model number")
        part_number = st.text_input("Part number")
        reference_tag = st.text_input("Reference tag")
        notes = st.text_area("Notes")
        submit_asset = st.form_submit_button("Add asset")
        if submit_asset and asset_type:
            session.add(EquipmentAsset(vessel_id=vessel.id, asset_type=asset_type, manufacturer=manufacturer, model_number=model_number, part_number=part_number, reference_tag=reference_tag, notes=notes))
            session.commit()
            st.success("Equipment asset added")
