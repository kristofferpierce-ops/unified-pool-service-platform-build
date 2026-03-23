from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st
from sqlmodel import Session, select

from app.core.database import create_db_and_tables, engine
from app.models.tables import Account, PoolVessel, Property
from app.services.bootstrap import seed_defaults

st.set_page_config(page_title="Pool Service Pricing Platform", layout="wide")

create_db_and_tables()
with Session(engine) as session:
    seed_defaults(session)

st.title("Pool Service Pricing Platform v2")
st.caption("Residential and commercial pricing, chemistry modeling, invoice review, direct deliveries, and calibration.")

with Session(engine) as session:
    accounts_count = len(list(session.exec(select(Account)).all()))
    properties_count = len(list(session.exec(select(Property)).all()))
    vessels_count = len(list(session.exec(select(PoolVessel)).all()))

c1, c2, c3, c4 = st.columns(4)
c1.metric("Accounts", accounts_count)
c2.metric("Properties", properties_count)
c3.metric("Vessels", vessels_count)
c4.metric("Pages", 9)

st.write("Use the left sidebar pages to manage shared costs, model versions, account records, estimators, commercial deliveries, invoice review, compare/train workflows, and growth-friendly operational tools.")
