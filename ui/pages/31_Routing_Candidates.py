from __future__ import annotations

import json
import os
from typing import Any

import requests
import streamlit as st


st.set_page_config(page_title="Routing Candidates", page_icon="🗂️", layout="wide")

PLATFORM_API = os.getenv("PLATFORM_API_BASE_URL", "http://127.0.0.1:8010")


def get_json(url: str) -> tuple[bool, Any]:
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return True, response.json()
    except Exception as exc:  # pragma: no cover - runtime display
        return False, str(exc)


st.title("🗂️ Phase 19 Routing Candidates")
st.caption("Read-only platform schema/API foundation for future RoutingPreferenceCandidate rows.")

st.warning(
    "This page is read-only. Step 29 does not import candidates, does not save routing rules, "
    "does not call bridge POST endpoints, and does not call LACRM."
)

status_ok, status = get_json(f"{PLATFORM_API}/front-desk/routing/candidates/status")
candidates_ok, candidates_payload = get_json(f"{PLATFORM_API}/front-desk/routing/candidates?limit=250")

if not status_ok:
    st.error(f"Could not read routing candidate status: {status}")
    st.stop()

c1, c2, c3, c4 = st.columns(4)
c1.metric("Schema", status.get("schema_version", "unknown"))
c2.metric("Total candidates", status.get("total_candidates", 0))
c3.metric("Import enabled", str(bool(status.get("candidate_import_enabled"))))
c4.metric("Bridge writes", "OFF" if not status.get("bridge_post_enabled") else "CHECK")

if status.get("read_only") and not status.get("candidate_import_enabled") and not status.get("routing_write_endpoint_implemented"):
    st.success("Safe schema foundation confirmed: read-only API, no importer, no routing write endpoint.")
else:
    st.error("Review routing candidate safety flags before continuing.")

st.subheader("Candidate status")
st.json(status)

st.subheader("Candidates")
if candidates_ok:
    rows = candidates_payload.get("candidates", []) if isinstance(candidates_payload, dict) else []
    if rows:
        st.dataframe(rows, use_container_width=True, hide_index=True)
    else:
        st.info("No routing candidates exist yet. This is expected in Step 29 because import is not implemented.")
else:
    st.warning(f"Could not read routing candidates: {candidates_payload}")

st.download_button(
    "Download routing candidate status JSON",
    json.dumps(status, indent=2, default=str),
    "phase19_routing_candidate_status.json",
    "application/json",
)

if candidates_ok:
    st.download_button(
        "Download routing candidates JSON",
        json.dumps(candidates_payload, indent=2, default=str),
        "phase19_routing_candidates.json",
        "application/json",
    )
