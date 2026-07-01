from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import streamlit as st


st.set_page_config(page_title="Bridge Routing Write Implementation Plan", page_icon="🧩", layout="wide")

WORKSPACE = Path(os.getenv("KPS_WORKSPACE", r"C:\Users\krist\Desktop\unified_pool_service_platform_build"))
BACKUP_DIR = WORKSPACE / "backups"


def latest_plans(limit: int = 20) -> list[Path]:
    if not BACKUP_DIR.exists():
        return []
    return sorted(
        [
            p
            for p in BACKUP_DIR.glob("phase19_bridge_routing_write_implementation_plan_*")
            if p.is_dir() and (p / "phase19_bridge_routing_write_implementation_plan.json").exists()
        ],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )[:limit]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


st.title("🧩 Phase 19 Bridge Routing Write Implementation Plan")
st.caption("Design plan for a future guarded bridge routing write scaffold.")

st.warning(
    "This page is implementation-plan-only. It does not write to the bridge, does not save platform records, "
    "does not call bridge POST endpoints, does not add bridge write implementation, and does not call LACRM."
)

plans = latest_plans()
if not plans:
    st.info(
        "No bridge routing write implementation plan found yet. Run "
        "`scripts\\phase19_generate_bridge_routing_write_implementation_plan.ps1` from the platform repo."
    )
    st.stop()

choice = st.selectbox(
    "Implementation plan",
    options=list(range(len(plans))),
    format_func=lambda i: f"{plans[i].name} - {plans[i].stat().st_mtime_ns}",
)
plan_dir = plans[choice]
json_path = plan_dir / "phase19_bridge_routing_write_implementation_plan.json"
items_csv_path = plan_dir / "phase19_bridge_routing_write_implementation_plan_items.csv"
blockers_csv_path = plan_dir / "phase19_bridge_routing_write_implementation_plan_blockers.csv"
artifacts_csv_path = plan_dir / "phase19_bridge_routing_write_implementation_plan_artifacts.csv"
md_path = plan_dir / "phase19_bridge_routing_write_implementation_plan.md"

plan = load_json(json_path)
safety = plan.get("safety", {})
implementation = plan.get("implementation_plan", {})
items = plan.get("plan_items", [])
blockers = plan.get("blockers", [])
artifacts = plan.get("artifacts", [])

c1, c2, c3, c4 = st.columns(4)
c1.metric("Plan status", implementation.get("status", "unknown"))
c2.metric("Required blockers", implementation.get("required_blockers", 0))
c3.metric("Review items", implementation.get("review_items", 0))
c4.metric("Bridge POST", "Not called" if not safety.get("bridge_post_called") else "CHECK")

if (
    safety.get("bridge_routing_write_implementation_plan_only")
    and not safety.get("platform_db_mutation_performed")
    and not safety.get("bridge_post_called")
    and not safety.get("bridge_write_implementation_added")
):
    st.success("Safe implementation plan confirmed: no platform DB write, no bridge POST, no bridge write implementation.")
else:
    st.error("Review implementation plan safety flags before continuing.")

if implementation.get("status") == "blocked":
    st.error("Implementation plan is blocked. Resolve blockers before adding a write scaffold.")
elif implementation.get("status") == "operator_review_required_before_scaffold_design":
    st.warning("Operator review is required before scaffold design.")
else:
    st.success("Plan is ready for guarded scaffold design. This still does not allow execution.")

st.subheader("Implementation summary")
st.json(implementation)

st.subheader("Artifacts")
if artifacts:
    st.dataframe(artifacts, use_container_width=True, hide_index=True)
else:
    st.info("No artifacts were recorded.")

st.subheader("Future plan items")
if items:
    st.dataframe(items, use_container_width=True, hide_index=True)
else:
    st.info("No future plan items were recorded.")

st.subheader("Blockers / review items")
if blockers:
    severity_values = sorted({str(row.get("severity") or "unknown") for row in blockers})
    selected = st.multiselect("Severity filter", severity_values, default=severity_values)
    filtered = [row for row in blockers if str(row.get("severity") or "unknown") in selected]
    st.dataframe(filtered, use_container_width=True, hide_index=True)
else:
    st.success("No blockers or review items were recorded.")

st.subheader("Runtime status")
with st.expander("Runtime status"):
    st.json(plan.get("runtime_status", {}))

st.subheader("Report files")
st.code(
    "\n".join(
        [
            f"Folder: {plan_dir}",
            f"JSON: {json_path}",
            f"Items CSV: {items_csv_path}",
            f"Blockers CSV: {blockers_csv_path}",
            f"Artifacts CSV: {artifacts_csv_path}",
            f"Markdown: {md_path}",
        ]
    ),
    language="text",
)

for label, path, filename in [
    ("Download plan items CSV", items_csv_path, "phase19_bridge_routing_write_implementation_plan_items.csv"),
    ("Download blockers CSV", blockers_csv_path, "phase19_bridge_routing_write_implementation_plan_blockers.csv"),
    ("Download artifacts CSV", artifacts_csv_path, "phase19_bridge_routing_write_implementation_plan_artifacts.csv"),
]:
    if path.exists():
        st.download_button(label, path.read_text(encoding="utf-8-sig"), filename, "text/csv")

st.download_button(
    "Download implementation plan JSON",
    json.dumps(plan, indent=2, default=str),
    "phase19_bridge_routing_write_implementation_plan.json",
    "application/json",
)

with st.expander("Raw implementation plan JSON"):
    st.json(plan)
