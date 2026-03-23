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
from app.models.tables import EstimateScenario, PoolVessel, Property
from app.services.baseline import get_active_model
from app.services.estimator import EstimateInput, calculate_estimate, save_estimate_run

st.title("Residential Estimator")

with Session(engine) as session:
    properties = list(session.exec(select(Property).where(Property.account_type == "residential")).all())
    if not properties:
        st.info("Create a residential property first on the Accounts & Properties page.")
        st.stop()
    prop_map = {f"{p.name} | {p.address_line_1}": p for p in properties}
    prop = prop_map[st.selectbox("Property", list(prop_map.keys()))]
    vessels = list(session.exec(select(PoolVessel).where(PoolVessel.property_id == prop.id)).all())
    vessel_map = {v.name: v for v in vessels}
    vessel = vessel_map[st.selectbox("Vessel", list(vessel_map.keys()))]

    c1, c2, c3 = st.columns(3)
    gallons = c1.number_input("Gallons", min_value=0.0, value=vessel.gallons)
    visits_per_month = c2.number_input("Visits per month", min_value=1.0, value=vessel.service_frequency_per_month)
    minutes_on_site = c3.number_input("Minutes on site", min_value=0.0, value=vessel.minutes_on_site)
    d1, d2, d3 = st.columns(3)
    drive_minutes = d1.number_input("Drive minutes round trip", min_value=0.0, value=prop.drive_minutes_round_trip)
    techs_on_visit = d2.number_input("Techs on visit", min_value=1, value=1)
    target_margin = d3.number_input("Target margin %", min_value=0.0, value=35.0)
    e1, e2, e3, e4, e5, e6 = st.columns(6)
    bath = e1.slider("Bath", 1, 10, vessel.bathing_score)
    debris = e2.slider("Debris", 1, 10, vessel.debris_score)
    filtration = e3.slider("Filtration", 1, 10, vessel.filtration_score)
    overflow = e4.slider("Overflow", 1, 10, vessel.overflow_score)
    backwash = e5.slider("Backwash", 1, 10, vessel.backwash_score)
    global_adj = e6.number_input("Global adj %", value=0.0)
    scenario_name = st.text_input("Scenario name", value="baseline residential quote")

    if st.button("Run residential estimate", type="primary"):
        model = get_active_model(session, "residential")
        scenario = EstimateScenario(
            property_id=prop.id,
            vessel_id=vessel.id,
            scenario_name=scenario_name,
            model_family="residential",
            baseline_model_version_id=model.id,
            target_margin_pct=target_margin,
            global_adjustment_pct=global_adj,
        )
        session.add(scenario)
        session.commit()
        session.refresh(scenario)
        estimate_input = EstimateInput(
            property_id=prop.id, vessel_id=vessel.id, model_family="residential", gallons=gallons,
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
        m3.metric("Per visit sell price", f"${output.visit_sell_price:,.2f}")
        chem_df = pd.DataFrame([
            {
                "Chemical": k,
                "Annual Qty": v["annual_quantity"],
                "Monthly Qty": v["monthly_quantity"],
                "Condition Multiplier": v["condition_multiplier"],
                "Annual Cost": output.chemical_costs[k]["annual_cost"],
            }
            for k, v in output.chemical_quantities.items()
        ])
        st.dataframe(chem_df, use_container_width=True, hide_index=True)
