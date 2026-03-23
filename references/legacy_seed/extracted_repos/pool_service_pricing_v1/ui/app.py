from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st
from sqlmodel import Session, select

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.core.database import create_db_and_tables, engine
from app.models.tables import (
    BaselineModelVersion,
    ChemicalCatalog,
    ChemicalCoefficient,
    ChemicalWeight,
    CompanyExpense,
    EstimateRun,
    FieldObservation,
    Property,
    SystemSetting,
)
from app.services.bootstrap import seed_defaults
from app.services.calibration import compare_estimate_to_observations
from app.services.estimator import EstimateInputs, run_estimate, save_estimate_run
from app.services.repositories import (
    get_active_baseline_model,
    get_estimate_runs_for_property,
    get_model_coefficients,
    get_model_weights,
    get_observations_for_property,
)

create_db_and_tables()
with Session(engine) as bootstrap_session:
    seed_defaults(bootstrap_session)

st.set_page_config(page_title="Pool Service Pricing Platform", layout="wide")


@st.cache_data(ttl=2)
def load_properties() -> pd.DataFrame:
    with Session(engine) as session:
        rows = session.exec(select(Property).order_by(Property.property_name)).all()
        return pd.DataFrame([row.model_dump() for row in rows])


@st.cache_data(ttl=2)
def load_company_expenses() -> pd.DataFrame:
    with Session(engine) as session:
        rows = session.exec(select(CompanyExpense).order_by(CompanyExpense.category, CompanyExpense.expense_name)).all()
        return pd.DataFrame([row.model_dump() for row in rows])


@st.cache_data(ttl=2)
def load_settings() -> pd.DataFrame:
    with Session(engine) as session:
        rows = session.exec(select(SystemSetting).order_by(SystemSetting.key)).all()
        return pd.DataFrame([{"key": r.key, "value": r.value, "description": r.description} for r in rows])


@st.cache_data(ttl=2)
def load_chemical_catalog() -> pd.DataFrame:
    with Session(engine) as session:
        rows = session.exec(select(ChemicalCatalog).order_by(ChemicalCatalog.display_name)).all()
        return pd.DataFrame([row.model_dump() for row in rows])


@st.cache_data(ttl=2)
def load_model_versions() -> pd.DataFrame:
    with Session(engine) as session:
        rows = session.exec(select(BaselineModelVersion).order_by(BaselineModelVersion.created_at.desc())).all()
        return pd.DataFrame([row.model_dump() for row in rows])


@st.cache_data(ttl=2)
def load_model_coefficients(model_version_id: int) -> pd.DataFrame:
    with Session(engine) as session:
        rows = session.exec(
            select(ChemicalCoefficient).where(ChemicalCoefficient.model_version_id == model_version_id)
        ).all()
        return pd.DataFrame([row.model_dump() for row in rows])


@st.cache_data(ttl=2)
def load_model_weights(model_version_id: int) -> pd.DataFrame:
    with Session(engine) as session:
        rows = session.exec(select(ChemicalWeight).where(ChemicalWeight.model_version_id == model_version_id)).all()
        return pd.DataFrame([row.model_dump() for row in rows])


def clear_caches() -> None:
    load_properties.clear()
    load_company_expenses.clear()
    load_settings.clear()
    load_chemical_catalog.clear()
    load_model_versions.clear()
    load_model_coefficients.clear()
    load_model_weights.clear()


st.title("Pool Service Pricing Platform v1")
st.caption("Residential-first estimating app built for expansion into shared commercial pricing and training workflows.")

section = st.sidebar.radio(
    "Navigate",
    [
        "Home",
        "Admin Costs & Settings",
        "Baseline Models",
        "Properties",
        "Estimator",
        "Field Logs",
        "Compare / Train",
    ],
)


if section == "Home":
    properties_df = load_properties()
    expenses_df = load_company_expenses()
    models_df = load_model_versions()

    c1, c2, c3 = st.columns(3)
    c1.metric("Properties", len(properties_df))
    c2.metric("Expense rows", len(expenses_df))
    c3.metric("Model versions", len(models_df))

    st.subheader("Architecture")
    st.write(
        "This app separates shared company costs, baseline model versions, property records, saved estimate scenarios, and real-world observations so the baseline model stays clean while training data accumulates over time."
    )

    st.subheader("How the data flows")
    st.write("1. Shared admin data feeds every estimator.")
    st.write("2. Baseline model versions store chemistry assumptions separately from field logs.")
    st.write("3. Each property can hold multiple saved estimate scenarios.")
    st.write("4. Observations compare actual performance against a chosen estimate without overwriting the baseline.")


elif section == "Admin Costs & Settings":
    st.subheader("Company expense database")
    expenses_df = load_company_expenses()
    edited_expenses = st.data_editor(expenses_df, num_rows="dynamic", use_container_width=True, hide_index=True)

    if st.button("Save expense changes"):
        with Session(engine) as session:
            existing_rows = session.exec(select(CompanyExpense)).all()
            for row in existing_rows:
                session.delete(row)
            session.commit()
            for _, row in edited_expenses.fillna("").iterrows():
                session.add(
                    CompanyExpense(
                        category=str(row.get("category", "") or "general"),
                        expense_name=str(row.get("expense_name", "") or "unnamed_expense"),
                        annual_cost=float(row.get("annual_cost", 0.0) or 0.0),
                        notes=str(row.get("notes", "") or ""),
                    )
                )
            session.commit()
        clear_caches()
        st.success("Expense database updated.")

    st.subheader("System settings")
    settings_df = load_settings()
    edited_settings = st.data_editor(settings_df, num_rows="dynamic", use_container_width=True, hide_index=True)

    if st.button("Save setting changes"):
        with Session(engine) as session:
            existing_rows = session.exec(select(SystemSetting)).all()
            for row in existing_rows:
                session.delete(row)
            session.commit()
            for _, row in edited_settings.fillna("").iterrows():
                session.add(
                    SystemSetting(
                        key=str(row.get("key", "") or "setting_key"),
                        value=float(row.get("value", 0.0) or 0.0),
                        description=str(row.get("description", "") or ""),
                    )
                )
            session.commit()
        clear_caches()
        st.success("System settings updated.")

    st.subheader("Chemical unit costs")
    chemicals_df = load_chemical_catalog()
    edited_chemicals = st.data_editor(chemicals_df, num_rows="dynamic", use_container_width=True, hide_index=True)

    if st.button("Save chemical cost changes"):
        with Session(engine) as session:
            existing_rows = session.exec(select(ChemicalCatalog)).all()
            for row in existing_rows:
                session.delete(row)
            session.commit()
            for _, row in edited_chemicals.fillna("").iterrows():
                session.add(
                    ChemicalCatalog(
                        key=str(row.get("key", "") or "chemical_key"),
                        display_name=str(row.get("display_name", "") or "Chemical"),
                        unit_name=str(row.get("unit_name", "") or "unit"),
                        default_unit_cost=float(row.get("default_unit_cost", 0.0) or 0.0),
                        active=bool(row.get("active", True)),
                    )
                )
            session.commit()
        clear_caches()
        st.success("Chemical catalog updated.")


elif section == "Baseline Models":
    models_df = load_model_versions()
    if models_df.empty:
        st.warning("No baseline models found.")
    else:
        st.subheader("Available baseline models")
        st.dataframe(models_df, use_container_width=True, hide_index=True)
        model_id = int(st.selectbox("Select baseline model", options=models_df["id"].tolist(), format_func=lambda x: models_df.loc[models_df["id"] == x, "name"].iloc[0]))

        st.subheader("Chemical coefficients")
        coeff_df = load_model_coefficients(model_id)
        edited_coeff_df = st.data_editor(coeff_df, use_container_width=True, hide_index=True, num_rows="dynamic")
        if st.button("Save coefficient changes"):
            with Session(engine) as session:
                existing_rows = session.exec(select(ChemicalCoefficient).where(ChemicalCoefficient.model_version_id == model_id)).all()
                for row in existing_rows:
                    session.delete(row)
                session.commit()
                for _, row in edited_coeff_df.fillna("").iterrows():
                    session.add(
                        ChemicalCoefficient(
                            model_version_id=model_id,
                            chemical_key=str(row.get("chemical_key", "") or "chemical_key"),
                            annual_coefficient_per_pool_gallon=float(row.get("annual_coefficient_per_pool_gallon", 0.0) or 0.0),
                        )
                    )
                session.commit()
            clear_caches()
            st.success("Model coefficients updated.")

        st.subheader("Weighting model")
        weights_df = load_model_weights(model_id)
        edited_weights_df = st.data_editor(weights_df, use_container_width=True, hide_index=True, num_rows="dynamic")
        if st.button("Save weight changes"):
            with Session(engine) as session:
                existing_rows = session.exec(select(ChemicalWeight).where(ChemicalWeight.model_version_id == model_id)).all()
                for row in existing_rows:
                    session.delete(row)
                session.commit()
                for _, row in edited_weights_df.fillna("").iterrows():
                    session.add(
                        ChemicalWeight(
                            model_version_id=model_id,
                            chemical_key=str(row.get("chemical_key", "") or "chemical_key"),
                            bath_weight=float(row.get("bath_weight", 0.0) or 0.0),
                            debris_weight=float(row.get("debris_weight", 0.0) or 0.0),
                            filtration_weight=float(row.get("filtration_weight", 0.0) or 0.0),
                            overflow_weight=float(row.get("overflow_weight", 0.0) or 0.0),
                            backwash_weight=float(row.get("backwash_weight", 0.0) or 0.0),
                        )
                    )
                session.commit()
            clear_caches()
            st.success("Model weights updated.")

        st.subheader("Create a new model version")
        with st.form("create_model_form"):
            new_model_name = st.text_input("New model name")
            new_model_description = st.text_area("Description")
            new_pool_type = st.selectbox("Pool type", ["residential", "commercial"])
            submitted = st.form_submit_button("Create model")
            if submitted and new_model_name.strip():
                with Session(engine) as session:
                    current_model = session.get(BaselineModelVersion, model_id)
                    new_model = BaselineModelVersion(
                        name=new_model_name.strip(),
                        description=new_model_description,
                        pool_type=new_pool_type,
                        active=True,
                        climate_profile_id=current_model.climate_profile_id,
                        water_profile_id=current_model.water_profile_id,
                    )
                    session.add(new_model)
                    session.commit()
                    session.refresh(new_model)

                    current_coeffs = session.exec(select(ChemicalCoefficient).where(ChemicalCoefficient.model_version_id == model_id)).all()
                    current_weights = session.exec(select(ChemicalWeight).where(ChemicalWeight.model_version_id == model_id)).all()
                    for row in current_coeffs:
                        session.add(
                            ChemicalCoefficient(
                                model_version_id=new_model.id,
                                chemical_key=row.chemical_key,
                                annual_coefficient_per_pool_gallon=row.annual_coefficient_per_pool_gallon,
                            )
                        )
                    for row in current_weights:
                        session.add(
                            ChemicalWeight(
                                model_version_id=new_model.id,
                                chemical_key=row.chemical_key,
                                bath_weight=row.bath_weight,
                                debris_weight=row.debris_weight,
                                filtration_weight=row.filtration_weight,
                                overflow_weight=row.overflow_weight,
                                backwash_weight=row.backwash_weight,
                            )
                        )
                    session.commit()
                clear_caches()
                st.success("New model version created from the selected baseline.")


elif section == "Properties":
    st.subheader("Property records")
    properties_df = load_properties()
    if not properties_df.empty:
        st.dataframe(properties_df, use_container_width=True, hide_index=True)

    st.subheader("Add property")
    with st.form("property_form"):
        property_name = st.text_input("Property name")
        address_line_1 = st.text_input("Address")
        city = st.text_input("City", value="Key West")
        state = st.text_input("State", value="FL")
        postal_code = st.text_input("Postal code")
        pool_gallons = st.number_input("Pool gallons", min_value=0.0, value=15000.0, step=500.0)
        covered = st.checkbox("Covered most of the time", value=False)
        visits_per_month = st.number_input("Visits per month", min_value=1.0, value=4.0, step=1.0)
        minutes_on_site = st.number_input("Minutes on site", min_value=0.0, value=25.0, step=5.0)
        drive_minutes_round_trip = st.number_input("Drive minutes round trip", min_value=0.0, value=20.0, step=5.0)
        notes = st.text_area("Notes")
        submitted = st.form_submit_button("Save property")
        if submitted and property_name.strip():
            with Session(engine) as session:
                session.add(
                    Property(
                        property_name=property_name.strip(),
                        address_line_1=address_line_1,
                        city=city,
                        state=state,
                        postal_code=postal_code,
                        pool_gallons=pool_gallons,
                        covered_most_of_time=covered,
                        visits_per_month=visits_per_month,
                        minutes_on_site=minutes_on_site,
                        drive_minutes_round_trip=drive_minutes_round_trip,
                        notes=notes,
                    )
                )
                session.commit()
            clear_caches()
            st.success("Property saved.")


elif section == "Estimator":
    properties_df = load_properties()
    if properties_df.empty:
        st.warning("Create a property first.")
    else:
        property_id = int(st.selectbox("Property", options=properties_df["id"].tolist(), format_func=lambda x: properties_df.loc[properties_df["id"] == x, "property_name"].iloc[0]))
        with Session(engine) as session:
            prop = session.get(Property, property_id)
            active_model = get_active_baseline_model(session, pool_type=prop.pool_type) or get_active_baseline_model(session, "residential")
            all_models = session.exec(select(BaselineModelVersion).order_by(BaselineModelVersion.created_at.desc())).all()
            model_map = {m.id: m.name for m in all_models}

        st.subheader("Scenario inputs")
        col1, col2 = st.columns(2)
        with col1:
            scenario_name = st.text_input("Scenario name", value="Baseline Quote")
            selected_model_id = int(st.selectbox("Model version", options=list(model_map.keys()), index=list(model_map.keys()).index(active_model.id) if active_model else 0, format_func=lambda x: model_map[x]))
            pool_gallons = st.number_input("Pool gallons", min_value=0.0, value=float(prop.pool_gallons), step=500.0)
            visits_per_month = st.number_input("Visits per month", min_value=1.0, value=float(prop.visits_per_month), step=1.0)
            minutes_on_site = st.number_input("Minutes on site", min_value=0.0, value=float(prop.minutes_on_site), step=5.0)
            drive_minutes = st.number_input("Drive minutes round trip", min_value=0.0, value=float(prop.drive_minutes_round_trip), step=5.0)
            techs_on_visit = st.number_input("Techs on visit", min_value=1, value=1, step=1)
        with col2:
            bath_score = st.slider("Bathing load", 1, 10, 5, help="1 = overloaded / heavy use, 10 = low use")
            debris_score = st.slider("Tree coverage / debris", 1, 10, 5, help="1 = heavy debris pressure, 10 = very clean")
            filtration_score = st.slider("Filtration quality", 1, 10, 5, help="1 = worst functional filtration, 10 = oversized and excellent")
            overflow_score = st.slider("Rain overflow / dilution", 1, 10, 5, help="1 = frequent overflow and dilution, 10 = very well controlled")
            annual_backwash_gallons = st.number_input("Annual backwash / waste gallons", min_value=0.0, value=0.0, step=100.0)
            global_adjustment_pct = st.number_input("Global adjustment %", value=0.0, step=1.0)
            settings_df = load_settings()
            default_margin = float(settings_df.loc[settings_df["key"] == "target_margin_pct", "value"].iloc[0]) if not settings_df.empty else 35.0
            target_margin_pct = st.number_input("Target margin %", value=default_margin, step=1.0)

        notes = st.text_area("Estimate notes")

        if st.button("Run estimate"):
            with Session(engine) as session:
                inputs = EstimateInputs(
                    property_id=property_id,
                    model_version_id=selected_model_id,
                    scenario_name=scenario_name,
                    pool_gallons=pool_gallons,
                    visits_per_month=visits_per_month,
                    minutes_on_site=minutes_on_site,
                    drive_minutes_round_trip=drive_minutes,
                    techs_on_visit=int(techs_on_visit),
                    bath_score=bath_score,
                    debris_score=debris_score,
                    filtration_score=filtration_score,
                    overflow_score=overflow_score,
                    annual_backwash_gallons=annual_backwash_gallons,
                    global_adjustment_pct=global_adjustment_pct,
                    target_margin_pct=target_margin_pct,
                    notes=notes,
                )
                result = run_estimate(session, inputs)
                st.session_state["latest_estimate_inputs"] = inputs
                st.session_state["latest_estimate_result"] = result

        result = st.session_state.get("latest_estimate_result")
        inputs = st.session_state.get("latest_estimate_inputs")
        if result:
            summary = result["summary"]
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Monthly real cost", f"${summary['monthly_real_cost']:,.2f}")
            m2.metric("Monthly sell price", f"${summary['monthly_sell_price']:,.2f}")
            m3.metric("Per visit sell price", f"${summary['visit_sell_price']:,.2f}")
            m4.metric("Annual real cost", f"${summary['annual_real_cost']:,.2f}")

            st.subheader("Chemistry detail")
            chem_df = pd.DataFrame(result["chemicals"])
            st.dataframe(chem_df, use_container_width=True, hide_index=True)

            st.subheader("Labor & overhead detail")
            labor_df = pd.DataFrame(
                [
                    {"Metric": "Adjusted site minutes", "Value": summary["adjusted_site_minutes"]},
                    {"Metric": "Hours per visit", "Value": summary["hours_per_visit"]},
                    {"Metric": "Burdened labor rate", "Value": summary["burdened_labor_rate"]},
                    {"Metric": "Overhead per hour", "Value": summary["overhead_per_hour"]},
                ]
            )
            st.dataframe(labor_df, use_container_width=True, hide_index=True)

            if st.button("Save estimate scenario"):
                with Session(engine) as session:
                    saved = save_estimate_run(session, inputs, result)
                st.success(f"Estimate scenario saved as run #{saved.id}.")

            st.download_button(
                label="Download estimate JSON",
                data=json.dumps(result, indent=2),
                file_name="estimate_result.json",
                mime="application/json",
            )


elif section == "Field Logs":
    properties_df = load_properties()
    if properties_df.empty:
        st.warning("Create a property first.")
    else:
        property_id = int(st.selectbox("Property", options=properties_df["id"].tolist(), format_func=lambda x: properties_df.loc[properties_df["id"] == x, "property_name"].iloc[0], key="field_property_id"))
        with Session(engine) as session:
            estimate_runs = get_estimate_runs_for_property(session, property_id)
            run_map = {0: "No linked estimate"}
            run_map.update({row.id: f"#{row.id} - {row.scenario_name}" for row in estimate_runs})

        st.subheader("Log real-world observation")
        with st.form("field_log_form"):
            estimate_run_id = int(st.selectbox("Linked estimate scenario", options=list(run_map.keys()), format_func=lambda x: run_map[x]))
            observed_on = st.date_input("Observed on")
            actual_site_minutes = st.number_input("Actual site minutes", min_value=0.0, value=25.0, step=5.0)
            actual_drive_minutes = st.number_input("Actual drive minutes round trip", min_value=0.0, value=20.0, step=5.0)

            st.write("Actual chemical usage logged for this observation")
            chemicals_df = load_chemical_catalog()
            actual_usage: dict[str, float] = {}
            cols = st.columns(2)
            for idx, (_, row) in enumerate(chemicals_df.iterrows()):
                with cols[idx % 2]:
                    actual_usage[row["key"]] = st.number_input(
                        f"{row['display_name']} ({row['unit_name']})",
                        min_value=0.0,
                        value=0.0,
                        step=0.1,
                        key=f"chem_{row['key']}",
                    )

            st.write("Actual test data")
            fc = st.number_input("Free chlorine", min_value=0.0, value=0.0, step=0.1)
            ph = st.number_input("pH", min_value=0.0, value=7.5, step=0.1)
            ta = st.number_input("Total alkalinity", min_value=0.0, value=0.0, step=1.0)
            ch = st.number_input("Calcium hardness", min_value=0.0, value=0.0, step=1.0)
            cya = st.number_input("CYA", min_value=0.0, value=0.0, step=1.0)
            notes = st.text_area("Observation notes")
            submitted = st.form_submit_button("Save observation")

            if submitted:
                with Session(engine) as session:
                    session.add(
                        FieldObservation(
                            property_id=property_id,
                            estimate_run_id=estimate_run_id or None,
                            observed_on=observed_on,
                            actual_site_minutes=actual_site_minutes,
                            actual_drive_minutes_round_trip=actual_drive_minutes,
                            actual_chemical_usage=actual_usage,
                            actual_test_data={"free_chlorine": fc, "ph": ph, "ta": ta, "ch": ch, "cya": cya},
                            notes=notes,
                        )
                    )
                    session.commit()
                st.success("Observation saved.")

        with Session(engine) as session:
            observations = get_observations_for_property(session, property_id)
        if observations:
            obs_df = pd.DataFrame([row.model_dump() for row in observations])
            st.subheader("Saved observations")
            st.dataframe(obs_df, use_container_width=True, hide_index=True)


elif section == "Compare / Train":
    properties_df = load_properties()
    if properties_df.empty:
        st.warning("Create a property first.")
    else:
        property_id = int(st.selectbox("Property", options=properties_df["id"].tolist(), format_func=lambda x: properties_df.loc[properties_df["id"] == x, "property_name"].iloc[0], key="compare_property_id"))
        with Session(engine) as session:
            estimate_runs = get_estimate_runs_for_property(session, property_id)
            if not estimate_runs:
                st.warning("Save at least one estimate scenario first.")
            else:
                run_id = int(st.selectbox("Estimate scenario", options=[row.id for row in estimate_runs], format_func=lambda x: next(row.scenario_name for row in estimate_runs if row.id == x)))
                selected_run = next(row for row in estimate_runs if row.id == run_id)
                observations = get_observations_for_property(session, property_id)
                if selected_run.id:
                    observations = [obs for obs in observations if obs.estimate_run_id in (None, selected_run.id)]
                comparison = compare_estimate_to_observations(selected_run, observations)

                st.subheader("Chemical comparison")
                chem_compare_df = pd.DataFrame(comparison["chemical_comparison"])
                st.dataframe(chem_compare_df, use_container_width=True, hide_index=True)

                st.subheader("Labor comparison")
                labor_compare_df = pd.DataFrame([comparison["labor_comparison"]])
                st.dataframe(labor_compare_df, use_container_width=True, hide_index=True)

                st.subheader("Training notes")
                st.write(
                    "This page compares a saved estimate scenario against actual logs without changing the baseline model version. Use variance patterns here to decide whether to build an account-specific calibrated scenario or create a new baseline model version."
                )
