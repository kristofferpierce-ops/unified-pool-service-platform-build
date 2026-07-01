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
from app.models.tables import BaselineModelVersion, ClimateProfile, WaterProfile
from app.utils.serialization import loads
from ui._shared import configure_page, page_header

configure_page('Baseline Models', icon='📐')
page_header('Baseline Models', 'Versioned pricing coefficients and climate/water profiles that drive the estimators.', icon='📐')

with Session(engine) as session:
    climates = list(session.exec(select(ClimateProfile)).all())
    waters = list(session.exec(select(WaterProfile)).all())
    models = list(session.exec(select(BaselineModelVersion).order_by(BaselineModelVersion.model_family, BaselineModelVersion.id)).all())

    st.subheader("Climate profiles")
    st.dataframe(pd.DataFrame([row.model_dump() for row in climates]), width='stretch', hide_index=True)

    st.subheader("Water profiles")
    st.dataframe(pd.DataFrame([row.model_dump() for row in waters]), width='stretch', hide_index=True)

    st.subheader("Model versions")
    model_labels = {f"{m.model_family} :: {m.version_name}": m.id for m in models}
    chosen = st.selectbox("Model version", list(model_labels.keys()))
    model = session.get(BaselineModelVersion, model_labels[chosen])
    st.write(model.description)
    st.json({"coefficients": loads(model.coefficients_json, {}), "weights": loads(model.weights_json, {})})
