from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import streamlit as st


st.set_page_config(page_title="Bridge Routing Network Transport Operator Signoff", page_icon="🖊️", layout="wide")

WORKSPACE = Path(os.getenv("KPS_WORKSPACE", r"C:\Users\krist\Desktop\unified_pool_service_platform_build"))
BACKUP_DIR = WORKSPACE / "backups"


def latest_reports(limit: int = 20) -> list[Path]:
    if not BACKUP_DIR.exists():
        return []
    return sorted(
        [
            p
            for p in BACKUP_DIR.glob("phase20_bridge_routing_network_transport_operator_signoff_*")
            if p.is_dir() and (p / "phase20_bridge_routing_network_transport_operator_signoff.json").exists()
        ],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )[:limit]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


st.title("🖊️ Phase 20 Bridge Routing Network Transport Operator Signoff")
st.caption("Operator signoff dossier for future network transport design review. This does not authorize bridge writes.")

st.warning(
    "This page is network-transport-operator-signoff-only. It does not write to the bridge, does not save platform records, "
    "does not call bridge POST endpoints, does not enable network transport, does not arm network transport, "
    "does not open network sockets, and does not call LACRM."
)

reports = latest_reports()
if not reports:
    st.info(
        "No bridge routing network transport operator signoff dossier found yet. Run "
        "`scripts\\phase20_generate_bridge_routing_network_transport_operator_signoff.ps1` from the platform repo."
    )
    st.stop()

choice = st.selectbox(
    "Network transport operator signoff dossier",
    options=list(range(len(reports))),
    format_func=lambda i: f"{reports[i].name} - {reports[i].stat().st_mtime_ns}",
)
report_dir = reports[choice]
json_path = report_dir / "phase20_bridge_routing_network_transport_operator_signoff.json"
checklist_csv_path = report_dir / "phase20_bridge_routing_network_transport_operator_signoff_checklist.csv"
issues_csv_path = report_dir / "phase20_bridge_routing_network_transport_operator_signoff_issues.csv"
md_path = report_dir / "phase20_bridge_routing_network_transport_operator_signoff.md"

report = load_json(json_path)
safety = report.get("safety", {})
signoff = report.get("signoff", {})
checklist = report.get("checklist", [])
issues = report.get("issues", [])

c1, c2, c3, c4 = st.columns(4)
c1.metric("Signoff status", signoff.get("status", "unknown"))
c2.metric("Blockers", signoff.get("blocker_count", 0))
c3.metric("Review items", signoff.get("review_count", 0))
c4.metric("Bridge POST", "Not called" if not safety.get("bridge_post_called") else "CHECK")

if (
    safety.get("bridge_routing_network_transport_operator_signoff_only")
    and safety.get("bridge_get_only")
    and not safety.get("platform_db_mutation_performed")
    and not safety.get("bridge_post_called")
    and not safety.get("network_transport_implemented")
    and not safety.get("network_socket_opened")
):
    st.success("Safe operator signoff confirmed: bridge GET only, no platform DB write, no bridge POST, no socket.")
else:
    st.error("Review network transport operator signoff safety flags before continuing.")

if signoff.get("status") == "blocked":
    st.error("Network transport operator signoff dossier is blocked. Resolve blockers before future real transport design.")
elif signoff.get("status") == "operator_review_required":
    st.warning("Operator review is required. This still does not authorize execution.")
else:
    st.success("Dossier is ready for operator network transport design review. This still does not authorize execution.")

st.subheader("Signoff summary")
st.json(signoff)

st.subheader("Operator attestation")
st.json(report.get("operator_attestation", {}))

st.subheader("Checklist")
if checklist:
    category_values = sorted({str(row.get("category") or "unknown") for row in checklist})
    selected_categories = st.multiselect("Category filter", category_values, default=category_values)
    filtered = [row for row in checklist if str(row.get("category") or "unknown") in selected_categories]
    st.dataframe(filtered, use_container_width=True, hide_index=True)
else:
    st.info("No checklist items were recorded.")

st.subheader("Issues")
if issues:
    severity_values = sorted({str(row.get("severity") or "unknown") for row in issues})
    selected_severity = st.multiselect("Severity filter", severity_values, default=severity_values)
    filtered_issues = [row for row in issues if str(row.get("severity") or "unknown") in selected_severity]
    st.dataframe(filtered_issues, use_container_width=True, hide_index=True)
else:
    st.success("No signoff issues were recorded.")

st.subheader("Runtime status")
with st.expander("Runtime status"):
    st.json(report.get("runtime_status", {}))

st.subheader("Report files")
st.code(
    "\n".join(
        [
            f"Folder: {report_dir}",
            f"JSON: {json_path}",
            f"Checklist CSV: {checklist_csv_path}",
            f"Issues CSV: {issues_csv_path}",
            f"Markdown: {md_path}",
        ]
    ),
    language="text",
)

for label, path, filename in [
    ("Download signoff checklist CSV", checklist_csv_path, "phase20_bridge_routing_network_transport_operator_signoff_checklist.csv"),
    ("Download signoff issues CSV", issues_csv_path, "phase20_bridge_routing_network_transport_operator_signoff_issues.csv"),
]:
    if path.exists():
        st.download_button(label, path.read_text(encoding="utf-8-sig"), filename, "text/csv")

st.download_button(
    "Download network transport operator signoff JSON",
    json.dumps(report, indent=2, default=str),
    "phase20_bridge_routing_network_transport_operator_signoff.json",
    "application/json",
)

with st.expander("Raw network transport operator signoff JSON"):
    st.json(report)
