from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import streamlit as st


st.set_page_config(page_title="Bridge Routing Write Contract", page_icon="📜", layout="wide")

WORKSPACE = Path(os.getenv("KPS_WORKSPACE", r"C:\Users\krist\Desktop\unified_pool_service_platform_build"))
BACKUP_DIR = WORKSPACE / "backups"


def latest_contracts(limit: int = 20) -> list[Path]:
    if not BACKUP_DIR.exists():
        return []
    return sorted(
        [p for p in BACKUP_DIR.glob("phase19_bridge_routing_write_contract_*") if p.is_dir()],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )[:limit]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


st.title("📜 Phase 19 Bridge Routing Write Contract")
st.caption("Read-only inspection of bridge routing UI/source markers and proposed write contract.")

st.warning(
    "This page is contract-only. It does not write to the bridge, does not save platform records, "
    "does not call bridge POST endpoints, and does not call LACRM."
)

contracts = latest_contracts()
if not contracts:
    st.info(
        "No bridge routing write contract found yet. Run "
        "`scripts\\phase19_generate_bridge_routing_write_contract.ps1` from the platform repo."
    )
    st.stop()

choice = st.selectbox(
    "Contract report",
    options=list(range(len(contracts))),
    format_func=lambda i: f"{contracts[i].name} — {contracts[i].stat().st_mtime_ns}",
)
contract_dir = contracts[choice]
json_path = contract_dir / "phase19_bridge_routing_write_contract.json"
matches_csv_path = contract_dir / "phase19_bridge_routing_write_contract_source_matches.csv"
md_path = contract_dir / "phase19_bridge_routing_write_contract.md"

contract = load_json(json_path)
safety = contract.get("safety", {})
markers = contract.get("bridge_ui_markers", {})
read_contract = contract.get("bridge_read_contract", {})
proposed = contract.get("proposed_write_contract", {})

c1, c2, c3, c4 = st.columns(4)
c1.metric("Bridge health", "OK" if contract.get("runtime", {}).get("bridge_health_ok") else "Check")
c2.metric("Routing UI", "Present" if markers.get("routing_rule_summary") else "Check")
c3.metric("Contract status", proposed.get("contract_status", "unknown"))
c4.metric("Bridge POST", "Not called" if not safety.get("bridge_post_called") else "CHECK")

if safety.get("bridge_routing_write_contract_only") and not safety.get("bridge_mutation_performed") and not safety.get("bridge_post_called"):
    st.success("Safe contract inspection confirmed: no bridge POST and no platform DB mutation.")
else:
    st.error("Review contract safety flags before continuing.")

st.subheader("Bridge UI markers")
st.json(markers)

st.subheader("Bridge read contract")
st.json(read_contract)

st.subheader("Proposed future write contract")
st.json(proposed)

st.subheader("Source inspection")
with st.expander("Source inspection details"):
    st.json(contract.get("source_inspection", {}))

st.subheader("Next recommended actions")
for item in contract.get("next_recommended_actions", []):
    st.markdown(f"- {item}")

st.subheader("Contract files")
st.code(
    "\n".join(
        [
            f"Folder: {contract_dir}",
            f"JSON: {json_path}",
            f"Source matches CSV: {matches_csv_path}",
            f"Markdown: {md_path}",
        ]
    ),
    language="text",
)

if matches_csv_path.exists():
    st.download_button(
        "Download source matches CSV",
        matches_csv_path.read_text(encoding="utf-8-sig"),
        "phase19_bridge_routing_write_contract_source_matches.csv",
        "text/csv",
    )

st.download_button(
    "Download contract JSON",
    json.dumps(contract, indent=2, default=str),
    "phase19_bridge_routing_write_contract.json",
    "application/json",
)

with st.expander("Raw contract JSON"):
    st.json(contract)
