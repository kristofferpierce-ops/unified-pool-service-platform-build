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
from app.models.tables import Account, PoolVessel, Property

st.title("Accounts & Properties")

with Session(engine) as session:
    st.subheader("Create account")
    with st.form("create_account"):
        name = st.text_input("Account name")
        account_type = st.selectbox("Account type", ["residential", "commercial"])
        billing_name = st.text_input("Billing name")
        notes = st.text_area("Notes")
        submitted = st.form_submit_button("Create account")
        if submitted and name:
            session.add(Account(name=name, account_type=account_type, billing_name=billing_name, notes=notes))
            session.commit()
            st.success("Account created")

    accounts = list(session.exec(select(Account).order_by(Account.account_type, Account.name)).all())
    st.dataframe(pd.DataFrame([row.model_dump() for row in accounts]), width='stretch', hide_index=True)

    st.subheader("Create property and vessel")
    if accounts:
        account_map = {f"{a.account_type} :: {a.name}": a.id for a in accounts}
        with st.form("create_property"):
            account_label = st.selectbox("Account", list(account_map.keys()))
            property_name = st.text_input("Property name")
            address = st.text_input("Address line 1")
            city = st.text_input("City", value="Key West")
            state = st.text_input("State", value="FL")
            postal_code = st.text_input("ZIP")
            drive_minutes = st.number_input("Drive minutes round trip", min_value=0.0, value=20.0)
            vessel_name = st.text_input("Primary vessel name", value="Main Pool")
            gallons = st.number_input("Gallons", min_value=0.0, value=15000.0, step=500.0)
            service_frequency = st.number_input("Service frequency per month", min_value=1.0, value=4.0)
            minutes_on_site = st.number_input("Minutes on site", min_value=0.0, value=25.0)
            create = st.form_submit_button("Create property + vessel")
            if create and property_name:
                account = session.get(Account, account_map[account_label])
                prop = Property(
                    account_id=account.id,
                    account_type=account.account_type,
                    name=property_name,
                    address_line_1=address,
                    city=city,
                    state=state,
                    postal_code=postal_code,
                    drive_minutes_round_trip=drive_minutes,
                )
                session.add(prop)
                session.commit()
                session.refresh(prop)
                session.add(PoolVessel(
                    property_id=prop.id,
                    name=vessel_name,
                    gallons=gallons,
                    service_frequency_per_month=service_frequency,
                    minutes_on_site=minutes_on_site,
                ))
                session.commit()
                st.success("Property and vessel created")

    properties = list(session.exec(select(Property).order_by(Property.account_type, Property.name)).all())
    vessels = list(session.exec(select(PoolVessel).order_by(PoolVessel.property_id, PoolVessel.name)).all())
    st.subheader("Properties")
    st.dataframe(pd.DataFrame([row.model_dump() for row in properties]), width='stretch', hide_index=True)
    st.subheader("Vessels")
    st.dataframe(pd.DataFrame([row.model_dump() for row in vessels]), width='stretch', hide_index=True)
