from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import streamlit as st


st.set_page_config(page_title="Bridge Routing HTTP Client Dry Run Validation", page_icon="🔍", layout="wide")

WORKSPACE = Path(os.getenv("KPS_WORKSPACE", r"C:\Users\krist\Desktop\unified_pool_service_platform_build"))
BACKUP_DIR = WORKSPACE / "backups"


def latest_reports(limit: int = 20) -> list[Path]:
    if not BACKUP_DIR.exists():
        return []
    return sorted(
        [
            p
            for p in BACKUP_DIR.glob("phase20_bridge_routing_http_client_dry_run_validation_*")
            if p.is_dir() and (p / "phase20_bridge_routing_http_client_dry_run_validation.json").exists()
        ],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )[:limit]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


st.title("🔍 Phase 20 Bridge Routing HTTP Client Dry Run Validation")
st.caption("Validation for the dry-run transport simulator. No real network transport and no bridge POST.")

st.warning(
    "This page is HTTP-client-dry-run-validation-only. It does not write to the bridge, does not save platform records, "
    "does not call bridge POST endpoints, does not add network transport, and does not call LACRM."
)

reports = latest_reports()
if not reports:
    st.info(
        "No bridge routing HTTP client dry-run validation report found yet. Run "
        "`scripts\\phase20_validate_bridge_routing_http_client_dry_run.ps1` from the platform repo."
    )
    st.stop()

choice = st.selectbox(
    "HTTP client dry-run validation report",
    options=list(range(len(reports))),
    format_func=lambda i: f"{reports[i].name} - {reports[i].stat().st_mtime_ns}",
)
report_dir = reports[choice]
json_path = report_dir / "phase20_bridge_routing_http_client_dry_run_validation.json"
gates_csv_path = report_dir / "phase20_bridge_routing_http_client_dry_run_validation_gates.csv"
issues_csv_path = report_dir / "phase20_bridge_routing_http_client_dry_run_validation_issues.csv"
request_csv_path = report_dir / "phase20_bridge_routing_http_client_dry_run_validation_request.csv"
md_path = report_dir / "phase20_bridge_routing_http_client_dry_run_validation.md"

report = load_json(json_path)
safety = report.get("safety", {})
validation = report.get("validation", {})
gates = report.get("gates", [])
issues = report.get("issues", [])

c1, c2, c3, c4 = st.columns(4)
c1.metric("Validation status", validation.get("status", "unknown"))
c2.metric("Blockers", validation.get("blocker_count", 0))
c3.metric("Review items", validation.get("review_count", 0))
c4.metric("Bridge POST", "Not called" if not safety.get("bridge_post_called") else "CHECK")

if (
    safety.get("bridge_routing_http_client_dry_run_validation_only")
    and safety.get("bridge_get_only")
    and not safety.get("platform_db_mutation_performed")
    and not safety.get("bridge_post_called")
    and not safety.get("network_transport_implemented")
):
    st.success("Safe dry-run validation confirmed: bridge GET only, no platform DB write, no bridge POST, no network transport.")
else:
    st.error("Review dry-run validation safety flags before continuing.")

if validation.get("status") == "blocked":
    st.error("Dry-run transport validation is blocked. Resolve blockers before any future network transport design.")
elif validation.get("status") == "valid_with_review_items":
    st.warning("Dry-run transport validation has review items. This still does not authorize execution.")
else:
    st.success("Dry-run transport is valid for review. This still does not authorize execution.")

st.subheader("Validation summary")
st.json(validation)

st.subheader("Simulated request")
st.json(report.get("simulated_request", {}))

st.subheader("Simulated response")
st.json(report.get("simulated_response", {}))

st.subheader("Gates")
if gates:
    severity_values = sorted({str(row.get("severity") or "unknown") for row in gates})
    selected_gate_severity = st.multiselect("Gate severity filter", severity_values, default=severity_values)
    filtered_gates = [row for row in gates if str(row.get("severity") or "unknown") in selected_gate_severity]
    st.dataframe(filtered_gates, use_container_width=True, hide_index=True)
else:
    st.info("No gates were recorded.")

st.subheader("Issues")
if issues:
    severity_values = sorted({str(row.get("severity") or "unknown") for row in issues})
    selected_issue_severity = st.multiselect("Issue severity filter", severity_values, default=severity_values)
    filtered_issues = [row for row in issues if str(row.get("severity") or "unknown") in selected_issue_severity]
    st.dataframe(filtered_issues, use_container_width=True, hide_index=True)
else:
    st.success("No validation issues were recorded.")

st.subheader("Runtime status")
with st.expander("Runtime status"):
    st.json(report.get("runtime_status", {}))

st.subheader("Report files")
st.code(
    "\n".join(
        [
            f"Folder: {report_dir}",
            f"JSON: {json_path}",
            f"Gates CSV: {gates_csv_path}",
            f"Issues CSV: {issues_csv_path}",
            f"Request CSV: {request_csv_path}",
            f"Markdown: {md_path}",
        ]
    ),
    language="text",
)

for label, path, filename in [
    ("Download gates CSV", gates_csv_path, "phase20_bridge_routing_http_client_dry_run_validation_gates.csv"),
    ("Download issues CSV", issues_csv_path, "phase20_bridge_routing_http_client_dry_run_validation_issues.csv"),
    ("Download request CSV", request_csv_path, "phase20_bridge_routing_http_client_dry_run_validation_request.csv"),
]:
    if path.exists():
        st.download_button(label, path.read_text(encoding="utf-8-sig"), filename, "text/csv")

st.download_button(
    "Download dry-run validation JSON",
    json.dumps(report, indent=2, default=str),
    "phase20_bridge_routing_http_client_dry_run_validation.json",
    "application/json",
)

with st.expander("Raw dry-run validation JSON"):
    st.json(report)
