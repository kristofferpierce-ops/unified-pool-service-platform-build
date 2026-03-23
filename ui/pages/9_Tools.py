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
from app.models.tables import Account, ApprovedAgent, Property
from app.services.property_verification import (
    add_approved_agent,
    build_source_links,
    create_verification_case,
    list_approved_agents,
    list_verification_cases,
)
from app.services.tools import list_tools

st.title("Tools")
st.caption("Operational tools that sit beside the core estimating engines and can grow over time without corrupting baseline pricing or training data.")

with Session(engine) as session:
    tools = list_tools(session)
    if tools:
        st.subheader("Available tools")
        tools_df = pd.DataFrame([
            {
                "Category": tool.category,
                "Tool": tool.name,
                "Description": tool.description,
                "Page Key": tool.page_key,
            }
            for tool in tools
        ])
        st.dataframe(tools_df, width='stretch', hide_index=True)

    tab1, tab2, tab3 = st.tabs(["Property authority verification", "Approved agents", "Recent tool history"])

    with tab1:
        properties = list(session.exec(select(Property).order_by(Property.account_type, Property.name)).all())
        property_options = {"Manual address only": None}
        for prop in properties:
            label = f"{prop.account_type} :: {prop.name} :: {prop.address_line_1}".strip()
            property_options[label] = prop.id

        st.write("Use this tool to check whether a caller appears to be the verified owner, a likely authorized agent, someone who needs owner approval, or a high renter/guest risk.")
        with st.form("property_verification_form"):
            prop_label = st.selectbox("Property record", list(property_options.keys()))
            property_id = property_options[prop_label]
            selected_property = session.get(Property, property_id) if property_id else None

            input_address = st.text_input(
                "Address for lookup",
                value=selected_property.address_line_1 if selected_property else "",
                help="For now, this tool keeps the intake and review workflow inside the app. Public-record lookups can be added as source adapters later without changing the case model.",
            )
            caller_name = st.text_input("Caller name")
            caller_phone = st.text_input("Caller phone")
            caller_role = st.text_input("Caller role / claim", placeholder="property manager, tenant rep, owner, registered agent")
            owner_name = st.text_input("Public-record owner name", placeholder="Paste from Monroe County property search or parcel/GIS source")
            owner_mailing_address = st.text_input("Owner mailing address", placeholder="Optional")
            parcel_id = st.text_input("Parcel ID", placeholder="Optional")
            sunbiz_entity_name = st.text_input("Sunbiz entity name", placeholder="If owner is an LLC or corporation")
            sunbiz_role_matches = st.text_area("Sunbiz role matches or notes", placeholder="manager, member, president, registered agent")
            notes = st.text_area("Internal notes")
            submitted = st.form_submit_button("Evaluate authority")
            if submitted and input_address and caller_name:
                account_type = selected_property.account_type if selected_property else "residential"
                case = create_verification_case(
                    session=session,
                    property_id=property_id,
                    account_type=account_type,
                    input_address=input_address,
                    caller_name=caller_name,
                    caller_phone=caller_phone,
                    caller_role=caller_role,
                    owner_name=owner_name,
                    owner_mailing_address=owner_mailing_address,
                    parcel_id=parcel_id,
                    sunbiz_entity_name=sunbiz_entity_name,
                    sunbiz_role_matches=sunbiz_role_matches,
                    source_mode="manual",
                    raw_payload={
                        "source_links": build_source_links(input_address, sunbiz_entity_name or owner_name),
                    },
                    notes=notes,
                )
                if case.verification_status == "verified_owner":
                    st.success(f"Status: {case.verification_status}")
                elif case.verification_status == "likely_authorized_agent":
                    st.info(f"Status: {case.verification_status}")
                elif case.verification_status == "needs_owner_approval":
                    st.warning(f"Status: {case.verification_status}")
                else:
                    st.error(f"Status: {case.verification_status}")
                st.write(case.recommended_action)
                links = build_source_links(input_address, sunbiz_entity_name or owner_name)
                st.markdown(f"[Property Search]({links['property_search']})  |  [GIS/Maps]({links['gis_maps']})  |  [Sunbiz Search]({links['sunbiz_entity_search']})")

    with tab2:
        properties = list(session.exec(select(Property).order_by(Property.account_type, Property.name)).all())
        if not properties:
            st.info("Create at least one property record before adding approved agents.")
        else:
            property_map = {f"{p.account_type} :: {p.name} :: {p.address_line_1}": p.id for p in properties}
            with st.form("approved_agent_form"):
                prop_label = st.selectbox("Property", list(property_map.keys()))
                full_name = st.text_input("Approved agent full name")
                role_label = st.text_input("Role label", placeholder="property manager, HOA manager, family representative")
                company_name = st.text_input("Company")
                phone = st.text_input("Phone")
                email = st.text_input("Email")
                approval_source = st.text_input("Approval source", value="manual")
                notes = st.text_area("Notes")
                save_agent = st.form_submit_button("Add approved agent")
                if save_agent and full_name:
                    add_approved_agent(
                        session,
                        property_id=property_map[prop_label],
                        full_name=full_name,
                        role_label=role_label,
                        company_name=company_name,
                        phone=phone,
                        email=email,
                        approval_source=approval_source,
                        notes=notes,
                    )
                    st.success("Approved agent added")

            selected_prop_id = property_map[prop_label] if property_map else None
            agents = list_approved_agents(session, selected_prop_id) if selected_prop_id else []
            if agents:
                st.dataframe(pd.DataFrame([a.model_dump() for a in agents]), width='stretch', hide_index=True)

    with tab3:
        cases = list_verification_cases(session, limit=100)
        if cases:
            rows = []
            for case in cases:
                rows.append({
                    "Created": case.created_at,
                    "Account Type": case.account_type,
                    "Address": case.input_address,
                    "Caller": case.caller_name,
                    "Owner": case.owner_name,
                    "Status": case.verification_status,
                    "Recommended Action": case.recommended_action,
                })
            st.dataframe(pd.DataFrame(rows), width='stretch', hide_index=True)
        else:
            st.info("No property verification cases have been run yet.")
