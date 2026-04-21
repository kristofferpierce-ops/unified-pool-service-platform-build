from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import streamlit as st


st.set_page_config(page_title="Bridge Routing Write Dry-run Validation", page_icon="🔎", layout="wide")

WORKSPACE = Path(os.getenv("KPS_WORKSPACE", r"C:\Users\krist\Desktop\unified_pool_service_platform_build"))
BACKUP_DIR = WORKSPACE / "backups"


def latest_reports(limit: int = 20) -> list[Path]:
    if not BACKUP_DIR.exists():
        return []
    return sorted(
        [
            p
            for p in BACKUP_DIR.glob("phase19_bridge_routing_write_dry_run_validation_*")
            if p.is_dir() and (p / "phase19_bridge_routing_write_dry_run_validation.json").exists()
        ],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )[:limit]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


st.title("🔎 Phase 19 Bridge Routing Write Dry-run Validation")
st.caption("Validation report for the Step 46 dry-run request bundle.")

st.warning(
    "This page is dry-run-validation-only. It does not write to the bridge, does not save platform records, "
    "does not call bridge POST endpoints, does not add a bridge HTTP client, and does not call LACRM."
)

reports = latest_reports()
if not reports:
    st.info(
        "No bridge routing write dry-run validation report found yet. Run "
        "`scripts\\phase19_validate_bridge_routing_write_dry_run_bundle.ps1` from the platform repo."
    )
    st.stop()

choice = st.selectbox(
    "Dry-run validation report",
    options=list(range(len(reports))),
    format_func=lambda i: f"{reports[i].name} - {reports[i].stat().st_mtime_ns}",
)
report_dir = reports[choice]
json_path = report_dir / "phase19_bridge_routing_write_dry_run_validation.json"
rows_csv_path = report_dir / "phase19_bridge_routing_write_dry_run_validation_rows.csv"
issues_csv_path = report_dir / "phase19_bridge_routing_write_dry_run_validation_issues.csv"
md_path = report_dir / "phase19_bridge_routing_write_dry_run_validation.md"

report = load_json(json_path)
safety = report.get("safety", {})
validation = report.get("validation", {})
issues = report.get("issues", [])
rows = report.get("row_reports", [])

c1, c2, c3, c4 = st.columns(4)
c1.metric("Validation status", validation.get("status", "unknown"))
c2.metric("Blockers", validation.get("blocker_count", 0))
c3.metric("Review items", validation.get("review_count", 0))
c4.metric("Bridge POST", "Not called" if not safety.get("bridge_post_called") else "CHECK")

if (
    safety.get("bridge_routing_write_dry_run_validation_only")
    and safety.get("bridge_get_only")
    and not safety.get("platform_db_mutation_performed")
    and not safety.get("bridge_post_called")
    and not safety.get("bridge_http_client_implemented")
):
    st.success("Safe validation confirmed: bridge GET only, no platform DB write, no bridge POST, no HTTP client.")
else:
    st.error("Review validation safety flags before continuing.")

if validation.get("status") == "blocked":
    st.error("Dry-run validation is blocked. Resolve blockers before any future bridge HTTP client work.")
elif validation.get("status") == "valid_with_review_items":
    st.warning("Validation has review items. Resolve or accept them before future design.")
else:
    st.success("Dry-run bundle is structurally valid for review. This still does not allow execution.")

st.subheader("Validation summary")
st.json(validation)

st.subheader("Counts")
st.json(report.get("counts", {}))

st.subheader("Row reports")
if rows:
    status_values = sorted({str(row.get("row_status") or "unknown") for row in rows})
    selected = st.multiselect("Row status filter", status_values, default=status_values)
    filtered = [row for row in rows if str(row.get("row_status") or "unknown") in selected]
    st.dataframe(filtered, use_container_width=True, hide_index=True)
else:
    st.info("No row reports were recorded.")

st.subheader("Issues")
if issues:
    severity_values = sorted({str(row.get("severity") or "unknown") for row in issues})
    selected_severity = st.multiselect("Severity filter", severity_values, default=severity_values)
    filtered_issues = [row for row in issues if str(row.get("severity") or "unknown") in selected_severity]
    st.dataframe(filtered_issues, use_container_width=True, hide_index=True)
else:
    st.success("No validation issues were recorded.")

st.subheader("Platform status")
with st.expander("Platform status"):
    st.json(report.get("platform_status", {}))

st.subheader("Bridge status")
with st.expander("Bridge status"):
    st.json(report.get("bridge_status", {}))

st.subheader("Report files")
st.code(
    "\n".join(
        [
            f"Folder: {report_dir}",
            f"JSON: {json_path}",
            f"Rows CSV: {rows_csv_path}",
            f"Issues CSV: {issues_csv_path}",
            f"Markdown: {md_path}",
        ]
    ),
    language="text",
)

for label, path, filename in [
    ("Download validation rows CSV", rows_csv_path, "phase19_bridge_routing_write_dry_run_validation_rows.csv"),
    ("Download validation issues CSV", issues_csv_path, "phase19_bridge_routing_write_dry_run_validation_issues.csv"),
]:
    if path.exists():
        st.download_button(label, path.read_text(encoding="utf-8-sig"), filename, "text/csv")

st.download_button(
    "Download dry-run validation JSON",
    json.dumps(report, indent=2, default=str),
    "phase19_bridge_routing_write_dry_run_validation.json",
    "application/json",
)

with st.expander("Raw validation JSON"):
    st.json(report)
