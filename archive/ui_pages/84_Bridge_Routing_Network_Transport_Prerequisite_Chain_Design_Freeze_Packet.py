from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import streamlit as st


st.set_page_config(page_title="Bridge Routing Network Transport Prerequisite Chain Design Freeze Packet", page_icon="🧷", layout="wide")

WORKSPACE = Path(os.getenv("KPS_WORKSPACE", r"C:\Users\krist\Desktop\unified_pool_service_platform_build"))
BACKUP_DIR = WORKSPACE / "backups"


def latest_reports(limit: int = 20) -> list[Path]:
    if not BACKUP_DIR.exists():
        return []
    return sorted(
        [
            p
            for p in BACKUP_DIR.glob("phase20_bridge_routing_network_transport_prerequisite_chain_design_freeze_packet_*")
            if p.is_dir() and (p / "phase20_bridge_routing_network_transport_prerequisite_chain_design_freeze_packet.json").exists()
        ],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )[:limit]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


st.title("🧷 Phase 20 Bridge Routing Network Transport Prerequisite Chain Design Freeze Packet")
st.caption("No-write design freeze packet for the network transport prerequisite chain.")

st.warning(
    "This page is network-transport-prerequisite-chain-design-freeze-packet-only. It does not create design-freeze records, "
    "does not record operator signoffs, does not create cutover packets, does not record cutover approvals, "
    "does not capture bridge responses, does not create response capture records, does not record operator approvals, "
    "does not create confirmation records, does not set environment variables, does not create rollback snapshots, "
    "does not create rollback rows, does not create audit rows, does not write to the bridge, does not save platform records, "
    "does not call bridge POST endpoints, does not enable network transport, does not arm network transport, "
    "does not open network sockets, and does not call LACRM."
)

reports = latest_reports()
if not reports:
    st.info(
        "No bridge routing network transport prerequisite chain design freeze packet found yet. Run "
        "`scripts\\phase20_generate_bridge_routing_network_transport_prerequisite_chain_design_freeze_packet.ps1` from the platform repo."
    )
    st.stop()

choice = st.selectbox(
    "Prerequisite chain design freeze packet",
    options=list(range(len(reports))),
    format_func=lambda i: f"{reports[i].name} - {reports[i].stat().st_mtime_ns}",
)
report_dir = reports[choice]
json_path = report_dir / "phase20_bridge_routing_network_transport_prerequisite_chain_design_freeze_packet.json"
checklist_csv_path = report_dir / "phase20_bridge_routing_network_transport_prerequisite_chain_design_freeze_packet_checklist.csv"
artifacts_csv_path = report_dir / "phase20_bridge_routing_network_transport_prerequisite_chain_design_freeze_packet_artifacts.csv"
issues_csv_path = report_dir / "phase20_bridge_routing_network_transport_prerequisite_chain_design_freeze_packet_issues.csv"
md_path = report_dir / "phase20_bridge_routing_network_transport_prerequisite_chain_design_freeze_packet.md"

report = load_json(json_path)
safety = report.get("safety", {})
packet = report.get("prerequisite_chain_design_freeze_packet", {})
artifacts = report.get("source_artifacts", [])
checklist = report.get("checklist", [])
issues = report.get("issues", [])

c1, c2, c3, c4 = st.columns(4)
c1.metric("Packet status", packet.get("status", "unknown"))
c2.metric("Artifacts", packet.get("artifact_count", 0))
c3.metric("Blockers", packet.get("blocker_count", 0))
c4.metric("Design freeze record", "Not created" if not safety.get("design_freeze_record_created") else "CHECK")

if (
    safety.get("bridge_routing_network_transport_prerequisite_chain_design_freeze_packet_only")
    and safety.get("bridge_get_only")
    and safety.get("design_freeze_packet_only")
    and not safety.get("design_freeze_record_created")
    and not safety.get("operator_signoff_recorded")
    and not safety.get("cutover_packet_created")
    and not safety.get("cutover_approval_recorded")
    and not safety.get("bridge_response_captured")
    and not safety.get("response_capture_record_created")
    and not safety.get("operator_approval_recorded")
    and not safety.get("confirmation_record_created")
    and not safety.get("environment_variables_set")
    and not safety.get("rollback_snapshot_created")
    and not safety.get("audit_row_created")
    and not safety.get("platform_db_mutation_performed")
    and not safety.get("bridge_post_called")
    and not safety.get("network_transport_implemented")
    and not safety.get("network_socket_opened")
):
    st.success("Safe design freeze packet confirmed: bridge GET only, no design-freeze record, no cutover packet, no records, no bridge POST, no socket.")
else:
    st.error("Review prerequisite chain design freeze packet safety flags before continuing.")

if packet.get("status") == "design_freeze_packet_blocked":
    st.error("Prerequisite chain design freeze packet is blocked. Resolve blockers before future real transport design.")
elif packet.get("status") == "design_freeze_packet_review_required_no_write":
    st.warning("Prerequisite chain design freeze packet has review items. This still does not authorize records or execution.")
else:
    st.success("Prerequisite chain design freeze packet is ready for review. This still does not authorize records or execution.")

st.subheader("Design freeze packet summary")
st.json(packet)

st.subheader("Source artifacts")
if artifacts:
    st.dataframe(artifacts, use_container_width=True, hide_index=True)
else:
    st.info("No source artifacts were recorded.")

st.subheader("Checklist")
if checklist:
    category_values = sorted({str(row.get("category") or "unknown") for row in checklist})
    selected_categories = st.multiselect("Checklist category filter", category_values, default=category_values)
    filtered_checklist = [row for row in checklist if str(row.get("category") or "unknown") in selected_categories]
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
    st.success("No prerequisite chain design freeze issues were recorded.")

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
            f"Artifacts CSV: {artifacts_csv_path}",
            f"Issues CSV: {issues_csv_path}",
            f"Markdown: {md_path}",
        ]
    ),
    language="text",
)

for label, path, filename in [
    ("Download checklist CSV", checklist_csv_path, "phase20_bridge_routing_network_transport_prerequisite_chain_design_freeze_packet_checklist.csv"),
    ("Download artifacts CSV", artifacts_csv_path, "phase20_bridge_routing_network_transport_prerequisite_chain_design_freeze_packet_artifacts.csv"),
    ("Download issues CSV", issues_csv_path, "phase20_bridge_routing_network_transport_prerequisite_chain_design_freeze_packet_issues.csv"),
]:
    if path.exists():
        st.download_button(label, path.read_text(encoding="utf-8-sig"), filename, "text/csv")

st.download_button(
    "Download prerequisite chain design freeze packet JSON",
    json.dumps(report, indent=2, default=str),
    "phase20_bridge_routing_network_transport_prerequisite_chain_design_freeze_packet.json",
    "application/json",
)

with st.expander("Raw prerequisite chain design freeze packet JSON"):
    st.json(report)
