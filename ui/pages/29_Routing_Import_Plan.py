from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import streamlit as st


st.set_page_config(page_title="Routing Import Plan", page_icon="📥", layout="wide")

WORKSPACE = Path(os.getenv("KPS_WORKSPACE", r"C:\Users\krist\Desktop\unified_pool_service_platform_build"))
BACKUP_DIR = WORKSPACE / "backups"


def latest_plans(limit: int = 20) -> list[Path]:
    if not BACKUP_DIR.exists():
        return []
    return sorted(
        [p for p in BACKUP_DIR.glob("phase19_routing_import_plan_*") if p.is_dir()],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )[:limit]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


st.title("📥 Phase 19 Routing Import Plan")
st.caption("Dry-run import plan for future RoutingPreferenceCandidate rows. No writes are performed.")

st.warning(
    "This page is import-plan-only. It does not save routing rules, does not write platform preferences, "
    "does not call bridge POST endpoints, and does not call LACRM."
)

plans = latest_plans()
if not plans:
    st.info(
        "No routing import plan found yet. Run "
        "`scripts\\phase19_generate_routing_import_plan.ps1` from the platform repo."
    )
    st.stop()

choice = st.selectbox(
    "Routing import plan",
    options=list(range(len(plans))),
    format_func=lambda i: f"{plans[i].name} — {plans[i].stat().st_mtime_ns}",
)
plan_dir = plans[choice]
json_path = plan_dir / "phase19_routing_import_plan.json"
csv_path = plan_dir / "phase19_routing_import_plan.csv"
md_path = plan_dir / "phase19_routing_import_plan.md"

plan = load_json(json_path)
safety = plan.get("safety", {})
validation_gate = plan.get("validation_gate", {})
counts = plan.get("counts", {})
rows = plan.get("import_plan_rows", [])

c1, c2, c3, c4 = st.columns(4)
c1.metric("Plan rows", counts.get("import_plan_rows", len(rows)))
c2.metric("Eligible", counts.get("eligible_for_future_dry_run_import", 0))
c3.metric("Validation errors", validation_gate.get("validation_errors", 0))
c4.metric("Import plan only", str(bool(safety.get("import_plan_only"))))

if safety.get("import_plan_only") and not safety.get("platform_db_mutation_performed") and not safety.get("bridge_mutation_performed"):
    st.success("Safe import plan confirmed: no platform DB write and no bridge mutation.")
else:
    st.error("Review import plan safety flags before continuing.")

if validation_gate.get("validation_errors", 0):
    st.warning("Validation errors exist. This plan is useful for review, but should not advance to an import checker yet.")
else:
    st.success("Validation gate is clear for a future dry-run-only import checker.")

st.subheader("Blocker summary")
st.json(counts.get("blocker_counts", {}))

st.subheader("Operator decision summary")
st.json(counts.get("operator_decision_counts", {}))

st.subheader("Import plan rows")
if rows:
    eligible_options = ["all", "eligible", "blocked"]
    eligibility = st.radio("Eligibility filter", eligible_options, horizontal=True)

    filtered = rows
    if eligibility == "eligible":
        filtered = [row for row in rows if row.get("eligible_for_future_dry_run_import")]
    elif eligibility == "blocked":
        filtered = [row for row in rows if not row.get("eligible_for_future_dry_run_import")]

    blocker_values = sorted({str(row.get("import_blocker") or "unknown") for row in filtered})
    selected_blockers = st.multiselect("Blocker filter", blocker_values, default=blocker_values)
    filtered = [row for row in filtered if str(row.get("import_blocker") or "unknown") in selected_blockers]

    st.dataframe(filtered, use_container_width=True, hide_index=True)
else:
    st.info("No import plan rows were generated.")

st.subheader("Proposed schema")
st.json(plan.get("proposed_schema", {}))

st.subheader("Plan files")
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
        "Download routing import plan CSV",
        csv_path.read_text(encoding="utf-8-sig"),
        "phase19_routing_import_plan.csv",
        "text/csv",
    )

st.download_button(
    "Download routing import plan JSON",
    json.dumps(plan, indent=2, default=str),
    "phase19_routing_import_plan.json",
    "application/json",
)

with st.expander("Raw import plan JSON"):
    st.json(plan)
