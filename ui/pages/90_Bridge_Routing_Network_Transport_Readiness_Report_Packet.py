from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import streamlit as st


st.set_page_config(page_title="Bridge Routing Network Transport Readiness Report Packet", page_icon="📋", layout="wide")

WORKSPACE = Path(os.getenv("KPS_WORKSPACE", r"C:\Users\krist\Desktop\unified_pool_service_platform_build"))
BACKUP_DIR = WORKSPACE / "backups"


def latest_reports(limit: int = 20) -> list[Path]:
    if not BACKUP_DIR.exists():
        return []
    return sorted(
        [
            p
            for p in BACKUP_DIR.glob("phase20_bridge_routing_network_transport_readiness_report_packet_*")
            if p.is_dir() and (p / "phase20_bridge_routing_network_transport_readiness_report_packet.json").exists()
        ],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )[:limit]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


st.title("📋 Phase 20 Bridge Routing Network Transport Readiness Report Packet")
st.caption("No-write readiness report packet for future bridge routing network transport work.")

st.warning(
    "This page is network-transport-readiness-report-packet-only. It shows readiness-report evidence. "
    "It does not create execution implementation, does not call interface execution methods, does not add a real bridge HTTP client, "
    "does not add network transport, does not enable network transport, does not arm network transport, "
    "does not open network sockets, does not call bridge POST endpoints, does not create design-freeze records, "
    "does not record operator signoffs, does not create cutover packets, does not record cutover approvals, "
    "does not capture bridge responses, does not create response capture records, does not record operator approvals, "
    "does not create confirmation records, does not set environment variables, does not create rollback snapshots, "
    "does not create rollback rows, does not create audit rows, does not write to the bridge, does not save platform records, "
    "and does not call LACRM."
)

reports = latest_reports()
if not reports:
    st.info(
        "No bridge routing network transport readiness report packet found yet. Run "
        "`scripts\\phase20_generate_bridge_routing_network_transport_readiness_report_packet.ps1` from the platform repo."
    )
    st.stop()

choice = st.selectbox(
    "Readiness report packet",
    options=list(range(len(reports))),
    format_func=lambda i: f"{reports[i].name} - {reports[i].stat().st_mtime_ns}",
)
report_dir = reports[choice]
json_path = report_dir / "phase20_bridge_routing_network_transport_readiness_report_packet.json"
methods_csv_path = report_dir / "phase20_bridge_routing_network_transport_readiness_report_packet_methods.csv"
checklist_csv_path = report_dir / "phase20_bridge_routing_network_transport_readiness_report_packet_checklist.csv"
artifacts_csv_path = report_dir / "phase20_bridge_routing_network_transport_readiness_report_packet_artifacts.csv"
issues_csv_path = report_dir / "phase20_bridge_routing_network_transport_readiness_report_packet_issues.csv"
md_path = report_dir / "phase20_bridge_routing_network_transport_readiness_report_packet.md"

report = load_json(json_path)
safety = report.get("safety", {})
packet = report.get("readiness_report_packet", {})
methods = report.get("report_methods", [])
artifacts = report.get("source_artifacts", [])
checklist = report.get("checklist", [])
issues = report.get("issues", [])

c1, c2, c3, c4 = st.columns(4)
c1.metric("Packet status", packet.get("status", "unknown"))
c2.metric("Report methods", packet.get("report_method_count", 0))
c3.metric("Blockers", packet.get("blocker_count", 0))
c4.metric("Execution implementation", "Not created" if not safety.get("execution_implementation_created") else "CHECK")

if (
    safety.get("bridge_routing_network_transport_readiness_report_packet_only")
    and safety.get("readiness_report_only")
    and safety.get("readiness_preview_created")
    and not safety.get("execution_implementation_created")
    and safety.get("bridge_get_only")
    and not safety.get("real_bridge_http_client_implemented")
    and not safety.get("network_transport_implemented")
    and not safety.get("network_socket_opened")
    and not safety.get("bridge_post_call_implemented")
    and not safety.get("bridge_post_called")
    and not safety.get("routing_write_endpoint_implemented")
    and not safety.get("bridge_response_captured")
    and not safety.get("audit_row_created")
    and not safety.get("platform_db_mutation_performed")
    and not safety.get("lacrm_call_performed")
):
    st.success("Safe readiness report confirmed: no-write report only, bridge GET only, no execution implementation, no transport, no bridge POST, no socket.")
else:
    st.error("Review readiness report packet safety flags before continuing.")

if packet.get("status") == "readiness_report_packet_blocked":
    st.error("Readiness report packet is blocked. Resolve blockers before future final review packet design.")
elif packet.get("status") == "readiness_report_packet_review_required_no_write":
    st.warning("Readiness report packet has review items. This still does not authorize execution implementation or network transport.")
else:
    st.success("Readiness report packet is ready for review. This still does not authorize execution implementation or network transport.")

st.subheader("Readiness report packet summary")
st.json(packet)

st.subheader("Report methods")
if methods:
    st.dataframe(methods, use_container_width=True, hide_index=True)
else:
    st.info("No report methods were recorded.")

st.subheader("Source artifacts")
if artifacts:
    st.dataframe(artifacts, use_container_width=True, hide_index=True)
else:
    st.info("No source artifacts were recorded.")

st.subheader("Checklist")
if checklist:
    category_values = sorted({str(row.get("category") or "unknown") for row in checklist})
    selected_checklist_categories = st.multiselect("Checklist category filter", category_values, default=category_values)
    filtered_checklist = [row for row in checklist if str(row.get("category") or "unknown") in selected_checklist_categories]
    st.dataframe(filtered_checklist, use_container_width=True, hide_index=True)
else:
    st.info("No checklist items were recorded.")

st.subheader("Issues")
if issues:
    severity_values = sorted({str(row.get("severity") or "unknown") for row in issues})
    selected_issue_severity = st.multiselect("Issue severity filter", severity_values, default=severity_values)
    filtered_issues = [row for row in issues if str(row.get("severity") or "unknown") in selected_issue_severity]
    st.dataframe(filtered_issues, use_container_width=True, hide_index=True)
else:
    st.success("No readiness report packet issues were recorded.")

st.subheader("Runtime status")
with st.expander("Runtime status"):
    st.json(report.get("runtime_status", {}))

st.subheader("Report files")
st.code(
    "\n".join(
        [
            f"Folder: {report_dir}",
            f"JSON: {json_path}",
            f"Methods CSV: {methods_csv_path}",
            f"Checklist CSV: {checklist_csv_path}",
            f"Artifacts CSV: {artifacts_csv_path}",
            f"Issues CSV: {issues_csv_path}",
            f"Markdown: {md_path}",
        ]
    ),
    language="text",
)

for label, path, filename in [
    ("Download methods CSV", methods_csv_path, "phase20_bridge_routing_network_transport_readiness_report_packet_methods.csv"),
    ("Download checklist CSV", checklist_csv_path, "phase20_bridge_routing_network_transport_readiness_report_packet_checklist.csv"),
    ("Download artifacts CSV", artifacts_csv_path, "phase20_bridge_routing_network_transport_readiness_report_packet_artifacts.csv"),
    ("Download issues CSV", issues_csv_path, "phase20_bridge_routing_network_transport_readiness_report_packet_issues.csv"),
]:
    if path.exists():
        st.download_button(label, path.read_text(encoding="utf-8-sig"), filename, "text/csv")

st.download_button(
    "Download readiness report packet JSON",
    json.dumps(report, indent=2, default=str),
    "phase20_bridge_routing_network_transport_readiness_report_packet.json",
    "application/json",
)

with st.expander("Raw readiness report packet JSON"):
    st.json(report)
