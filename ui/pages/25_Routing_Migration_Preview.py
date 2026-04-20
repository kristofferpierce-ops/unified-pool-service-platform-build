from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import streamlit as st


st.set_page_config(page_title="Routing Migration Preview", page_icon="🧪", layout="wide")

WORKSPACE = Path(os.getenv("KPS_WORKSPACE", r"C:\Users\krist\Desktop\unified_pool_service_platform_build"))
BACKUP_DIR = WORKSPACE / "backups"


def latest_previews(limit: int = 20) -> list[Path]:
    if not BACKUP_DIR.exists():
        return []
    return sorted(
        BACKUP_DIR.glob("phase19_routing_migration_preview_*.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )[:limit]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


st.title("🧪 Phase 19 Routing Migration Preview")
st.caption("Dry-run preview for mapping bridge routing rules into future platform RoutingPreference candidates.")

st.warning(
    "This page is preview-only. It does not save routing rules, does not write platform preferences, "
    "does not call bridge POST endpoints, and does not call LACRM."
)

previews = latest_previews()
if not previews:
    st.info(
        "No routing migration preview found yet. Run "
        "`scripts\\phase19_generate_routing_migration_preview.ps1` from the platform repo."
    )
    st.stop()

choice = st.selectbox(
    "Preview",
    options=list(range(len(previews))),
    format_func=lambda i: f"{previews[i].name} — {previews[i].stat().st_mtime_ns}",
)
path = previews[choice]
preview = load_json(path)

safety = preview.get("safety", {})
counts = preview.get("counts", {})
rows = preview.get("preview_rows", [])

c1, c2, c3, c4 = st.columns(4)
c1.metric("Preview rows", counts.get("preview_rows", len(rows)))
c2.metric("Source rules", counts.get("source_unique_rules", 0))
c3.metric("Preview only", str(bool(safety.get("preview_only"))))
c4.metric("Bridge writes", "OFF" if not safety.get("bridge_mutation_performed") else "CHECK")

if safety.get("preview_only") and not safety.get("platform_db_mutation_performed") and not safety.get("bridge_mutation_performed"):
    st.success("Safe preview confirmed: no platform DB write and no bridge mutation.")
else:
    st.error("Review safety flags before continuing.")

st.subheader("Risk summary")
st.json(counts.get("risk_counts", {}))

st.subheader("Proposed action summary")
st.json(counts.get("proposed_action_counts", {}))

st.subheader("Routing migration preview rows")
if rows:
    risk_values = sorted({str(row.get("risk_level") or "unknown") for row in rows})
    selected_risks = st.multiselect("Risk filter", risk_values, default=risk_values)

    action_values = sorted({str(row.get("proposed_action") or "unknown") for row in rows})
    selected_actions = st.multiselect("Action filter", action_values, default=action_values)

    filtered = [
        row for row in rows
        if str(row.get("risk_level") or "unknown") in selected_risks
        and str(row.get("proposed_action") or "unknown") in selected_actions
    ]

    st.dataframe(filtered, use_container_width=True, hide_index=True)
else:
    st.info("No preview rows were generated.")

st.subheader("Proposed schema")
st.json(preview.get("proposed_schema", {}))

st.subheader("Next recommended actions")
for item in preview.get("next_recommended_actions", []):
    st.markdown(f"- {item}")

with st.expander("Raw preview JSON"):
    st.json(preview)

st.download_button(
    "Download routing migration preview JSON",
    json.dumps(preview, indent=2, default=str),
    "phase19_routing_migration_preview.json",
    "application/json",
)
