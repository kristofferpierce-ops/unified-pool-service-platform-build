from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import streamlit as st


st.set_page_config(page_title="Routing Import Plan Validator", page_icon="🛡️", layout="wide")

WORKSPACE = Path(os.getenv("KPS_WORKSPACE", r"C:\Users\krist\Desktop\unified_pool_service_platform_build"))
BACKUP_DIR = WORKSPACE / "backups"


def latest_validations(limit: int = 20) -> list[Path]:
    if not BACKUP_DIR.exists():
        return []
    return sorted(
        [p for p in BACKUP_DIR.glob("phase19_routing_import_plan_validation_*") if p.is_dir()],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )[:limit]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


st.title("🛡️ Phase 19 Routing Import Plan Validator")
st.caption("Pre-persistence validation for future RoutingPreferenceCandidate import work.")

st.warning(
    "This page is validation-only. It does not save routing rules, does not write platform preferences, "
    "does not call bridge POST endpoints, and does not call LACRM."
)

validations = latest_validations()
if not validations:
    st.info(
        "No routing import plan validation found yet. Run "
        "`scripts\\phase19_validate_routing_import_plan.ps1` from the platform repo."
    )
    st.stop()

choice = st.selectbox(
    "Import plan validation",
    options=list(range(len(validations))),
    format_func=lambda i: f"{validations[i].name} — {validations[i].stat().st_mtime_ns}",
)
validation_dir = validations[choice]
json_path = validation_dir / "phase19_routing_import_plan_validation.json"
issues_csv_path = validation_dir / "phase19_routing_import_plan_validation_issues.csv"
rows_csv_path = validation_dir / "phase19_routing_import_plan_validation_rows.csv"
md_path = validation_dir / "phase19_routing_import_plan_validation.md"

validation = load_json(json_path)
safety = validation.get("safety", {})
gate = validation.get("validation_gate", {})
counts = validation.get("counts", {})
issues = validation.get("issues", [])
rows = validation.get("row_reports", [])

c1, c2, c3, c4 = st.columns(4)
c1.metric("Plan rows", counts.get("plan_rows", len(rows)))
c2.metric("Errors", counts.get("errors", 0))
c3.metric("Warnings", counts.get("warnings", 0))
c4.metric("Validation only", str(bool(safety.get("import_plan_validation_only"))))

if safety.get("import_plan_validation_only") and not safety.get("platform_db_mutation_performed") and not safety.get("bridge_mutation_performed"):
    st.success("Safe validation confirmed: no platform DB write and no bridge mutation.")
else:
    st.error("Review validation safety flags before continuing.")

if gate.get("can_create_future_candidate_importer"):
    st.success("Import plan passed validation. Next step may add schema only; writes should remain disabled.")
else:
    st.warning("Import plan has validation errors or blockers. Resolve before candidate importer work.")

st.subheader("Validation gate")
st.json(gate)

st.subheader("Blocker summary")
st.json(counts.get("blocker_counts", {}))

st.subheader("Issues")
if issues:
    severity_values = sorted({str(issue.get("severity") or "unknown") for issue in issues})
    selected = st.multiselect("Severity filter", severity_values, default=severity_values)
    filtered = [issue for issue in issues if str(issue.get("severity") or "unknown") in selected]
    st.dataframe(filtered, use_container_width=True, hide_index=True)
else:
    st.info("No validation issues were recorded.")

st.subheader("Row reports")
if rows:
    eligibility = st.radio("Eligibility filter", ["all", "eligible", "blocked"], horizontal=True)
    filtered_rows = rows
    if eligibility == "eligible":
        filtered_rows = [row for row in rows if row.get("eligible_for_future_dry_run_import")]
    elif eligibility == "blocked":
        filtered_rows = [row for row in rows if not row.get("eligible_for_future_dry_run_import")]
    st.dataframe(filtered_rows, use_container_width=True, hide_index=True)
else:
    st.info("No row reports were recorded.")

st.subheader("Validation files")
st.code(
    "\n".join(
        [
            f"Folder: {validation_dir}",
            f"JSON: {json_path}",
            f"Issues CSV: {issues_csv_path}",
            f"Rows CSV: {rows_csv_path}",
            f"Markdown: {md_path}",
        ]
    ),
    language="text",
)

if issues_csv_path.exists():
    st.download_button(
        "Download validation issues CSV",
        issues_csv_path.read_text(encoding="utf-8-sig"),
        "phase19_routing_import_plan_validation_issues.csv",
        "text/csv",
    )

if rows_csv_path.exists():
    st.download_button(
        "Download validation rows CSV",
        rows_csv_path.read_text(encoding="utf-8-sig"),
        "phase19_routing_import_plan_validation_rows.csv",
        "text/csv",
    )

st.download_button(
    "Download validation JSON",
    json.dumps(validation, indent=2, default=str),
    "phase19_routing_import_plan_validation.json",
    "application/json",
)

with st.expander("Raw validation JSON"):
    st.json(validation)
