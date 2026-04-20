from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st


st.set_page_config(page_title="Routing Worksheet Validator", page_icon="✅", layout="wide")

WORKSPACE = Path(os.getenv("KPS_WORKSPACE", r"C:\Users\krist\Desktop\unified_pool_service_platform_build"))
BACKUP_DIR = WORKSPACE / "backups"


def latest_validations(limit: int = 20) -> list[Path]:
    if not BACKUP_DIR.exists():
        return []
    return sorted(
        [p for p in BACKUP_DIR.glob("phase19_routing_worksheet_validation_*") if p.is_dir()],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )[:limit]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


st.title("✅ Phase 19 Routing Worksheet Validator")
st.caption("Dry-run validation report for routing approval worksheets.")

st.warning(
    "This page is validation-only. It does not save routing rules, does not write platform preferences, "
    "does not call bridge POST endpoints, and does not call LACRM."
)

validations = latest_validations()
if not validations:
    st.info(
        "No routing worksheet validation found yet. Run "
        "`scripts\\phase19_validate_routing_worksheet.ps1` from the platform repo."
    )
    st.stop()

choice = st.selectbox(
    "Validation report",
    options=list(range(len(validations))),
    format_func=lambda i: f"{validations[i].name} — {validations[i].stat().st_mtime_ns}",
)
validation_dir = validations[choice]
json_path = validation_dir / "phase19_routing_worksheet_validation.json"
issues_csv_path = validation_dir / "phase19_routing_worksheet_validation_issues.csv"
rows_csv_path = validation_dir / "phase19_routing_worksheet_validation_rows.csv"
md_path = validation_dir / "phase19_routing_worksheet_validation.md"

validation = load_json(json_path)
safety = validation.get("safety", {})
counts = validation.get("counts", {})
issues = validation.get("issues", [])
rows = validation.get("validated_rows", [])

c1, c2, c3, c4 = st.columns(4)
c1.metric("Rows checked", counts.get("rows_checked", len(rows)))
c2.metric("Errors", counts.get("errors", 0))
c3.metric("Warnings", counts.get("warnings", 0))
c4.metric("Validation only", str(bool(safety.get("validation_only"))))

if safety.get("validation_only") and not safety.get("platform_db_mutation_performed") and not safety.get("bridge_mutation_performed"):
    st.success("Safe validation confirmed: no platform DB write and no bridge mutation.")
else:
    st.error("Review validation safety flags before continuing.")

if counts.get("errors", 0):
    st.error("Resolve validation errors before any future dry-run import workflow.")
else:
    st.success("No validation errors were found.")

st.subheader("Operator decision summary")
st.json(counts.get("operator_decision_counts", {}))

st.subheader("Issues")
if issues:
    severity_values = sorted({str(issue.get("severity") or "unknown") for issue in issues})
    selected_severities = st.multiselect("Severity filter", severity_values, default=severity_values)
    filtered_issues = [issue for issue in issues if str(issue.get("severity") or "unknown") in selected_severities]
    st.dataframe(filtered_issues, use_container_width=True, hide_index=True)
else:
    st.info("No validation issues were recorded.")

st.subheader("Validated rows")
if rows:
    st.dataframe(rows, use_container_width=True, hide_index=True)
else:
    st.info("No validated rows were recorded.")

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
        "phase19_routing_worksheet_validation_issues.csv",
        "text/csv",
    )

if rows_csv_path.exists():
    st.download_button(
        "Download validation rows CSV",
        rows_csv_path.read_text(encoding="utf-8-sig"),
        "phase19_routing_worksheet_validation_rows.csv",
        "text/csv",
    )

st.download_button(
    "Download validation JSON",
    json.dumps(validation, indent=2, default=str),
    "phase19_routing_worksheet_validation.json",
    "application/json",
)

with st.expander("Raw validation JSON"):
    st.json(validation)
