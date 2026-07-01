from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import streamlit as st


st.set_page_config(page_title="Bridge Routing Write Audit Plan", page_icon="🧭", layout="wide")

WORKSPACE = Path(os.getenv("KPS_WORKSPACE", r"C:\Users\krist\Desktop\unified_pool_service_platform_build"))
BACKUP_DIR = WORKSPACE / "backups"


def latest_plans(limit: int = 20) -> list[Path]:
    if not BACKUP_DIR.exists():
        return []
    return sorted(
        [
            p
            for p in BACKUP_DIR.glob("phase19_bridge_routing_write_audit_plan_*")
            if p.is_dir() and (p / "phase19_bridge_routing_write_audit_plan.json").exists()
        ],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )[:limit]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


st.title("🧭 Phase 19 Bridge Routing Write Audit Plan")
st.caption("Dry-run audit-row plan from bridge routing write rehearsal output.")

st.warning(
    "This page is audit-plan-only. It does not create audit rows, does not write to the bridge, "
    "does not save platform records, does not call bridge POST endpoints, and does not call LACRM."
)

plans = latest_plans()
if not plans:
    st.info(
        "No bridge routing write audit plan found yet. Run "
        "`scripts\\phase19_plan_bridge_routing_write_audit.ps1` from the platform repo."
    )
    st.stop()

choice = st.selectbox(
    "Audit plan",
    options=list(range(len(plans))),
    format_func=lambda i: f"{plans[i].name} — {plans[i].stat().st_mtime_ns}",
)
plan_dir = plans[choice]
json_path = plan_dir / "phase19_bridge_routing_write_audit_plan.json"
csv_path = plan_dir / "phase19_bridge_routing_write_audit_plan.csv"
md_path = plan_dir / "phase19_bridge_routing_write_audit_plan.md"

report = load_json(json_path)
safety = report.get("safety", {})
counts = report.get("counts", {})
rows = report.get("plan_rows", [])
safety_errors = report.get("safety_errors", [])

c1, c2, c3, c4 = st.columns(4)
c1.metric("Rehearsal rows", counts.get("rehearsal_rows", 0))
c2.metric("Existing audit rows", counts.get("existing_audit_rows", 0))
c3.metric("Plan rows", counts.get("plan_rows", len(rows)))
c4.metric("Audit plan only", str(bool(safety.get("bridge_routing_write_audit_plan_only"))))

if (
    safety.get("bridge_routing_write_audit_plan_only")
    and not safety.get("platform_db_mutation_performed")
    and not safety.get("bridge_post_called")
):
    st.success("Safe audit plan confirmed: no platform DB write, no bridge POST, no LACRM call.")
else:
    st.error("Review audit plan safety flags before continuing.")

if safety_errors:
    st.error("Safety errors were found.")
    st.code("\n".join(str(x) for x in safety_errors), language="text")
else:
    st.success("Audit API safety flags are read-only.")

st.subheader("Plan action summary")
st.json(counts.get("action_counts", {}))

st.subheader("Audit plan rows")
if rows:
    action_values = sorted({str(row.get("plan_action") or "unknown") for row in rows})
    selected_actions = st.multiselect("Plan action filter", action_values, default=action_values)
    filtered = [row for row in rows if str(row.get("plan_action") or "unknown") in selected_actions]
    st.dataframe(filtered, use_container_width=True, hide_index=True)
else:
    st.info("No audit plan rows were generated.")

st.subheader("Report files")
st.code(
    "\n".join(
        [
            f"Folder: {plan_dir}",
            f"JSON: {json_path}",
            f"CSV: {csv_path}",
            f"Markdown: {md_path}",
        ]
    ),
    language="text",
)

if csv_path.exists():
    st.download_button(
        "Download audit plan CSV",
        csv_path.read_text(encoding="utf-8-sig"),
        "phase19_bridge_routing_write_audit_plan.csv",
        "text/csv",
    )

st.download_button(
    "Download audit plan JSON",
    json.dumps(report, indent=2, default=str),
    "phase19_bridge_routing_write_audit_plan.json",
    "application/json",
)

with st.expander("Raw audit plan JSON"):
    st.json(report)
