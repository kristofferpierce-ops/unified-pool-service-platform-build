from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import streamlit as st


st.set_page_config(page_title="Bridge Routing Network Transport Final Review Packet", page_icon="🏁", layout="wide")

WORKSPACE = Path(os.getenv("KPS_WORKSPACE", r"C:\Users\krist\Desktop\unified_pool_service_platform_build"))
BACKUP_DIR = WORKSPACE / "backups"


def latest_reports(limit: int = 20) -> list[Path]:
    if not BACKUP_DIR.exists():
        return []
    return sorted(
        [
            p
            for p in BACKUP_DIR.glob("phase20_bridge_routing_network_transport_final_review_packet_*")
            if p.is_dir() and (p / "phase20_bridge_routing_network_transport_final_review_packet.json").exists()
        ],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )[:limit]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


st.title("🏁 Phase 20 Bridge Routing Network Transport Final Review Packet")
st.caption("No-write final review packet for future bridge routing network transport work.")

st.warning(
    "This page is network-transport-final-review-packet-only. It shows final-review evidence. "
    "It does not record final approvals, does not create execution implementation, does not call interface execution methods, "
    "does not add a real bridge HTTP client, does not add network transport, does not enable network transport, "
    "does not arm network transport, does not open network sockets, does not call bridge POST endpoints, "
    "does not create design-freeze records, does not record operator signoffs, does not create cutover packets, "
    "does not record cutover approvals, does not capture bridge responses, does not create response capture records, "
    "does not record operator approvals, does not create confirmation records, does not set environment variables, "
    "does not create rollback snapshots, does not create rollback rows, does not create audit rows, "
    "does not write to the bridge, does not save platform records, and does not call LACRM."
)

reports = latest_reports()
if not reports:
    st.info(
        "No bridge routing network transport final review packet found yet. Run "
        "`scripts\\phase20_generate_bridge_routing_network_transport_final_review_packet.ps1` from the platform repo."
    )
    st.stop()

choice = st.selectbox(
    "Final review packet",
    options=list(range(len(reports))),
    format_func=lambda i: f"{reports[i].name} - {reports[i].stat().st_mtime_ns}",
)
report_dir = reports[choice]
json_path = report_dir / "phase20_bridge_routing_network_transport_final_review_packet.json"
methods_csv_path = report_dir / "phase20_bridge_routing_network_transport_final_review_packet_methods.csv"
checklist_csv_path = report_dir / "phase20_bridge_routing_network_transport_final_review_packet_checklist.csv"
artifacts_csv_path = report_dir / "phase20_bridge_routing_network_transport_final_review_packet_artifacts.csv"
issues_csv_path = report_dir / "phase20_bridge_routing_network_transport_final_review_packet_issues.csv"
md_path = report_dir / "phase20_bridge_routing_network_transport_final_review_packet.md"

report = load_json(json_path)
safety = report.get("safety", {})
packet = report.get("final_review_packet", {})
methods = report.get("packet_methods", [])
artifacts = report.get("source_artifacts", [])
checklist = report.get("checklist", [])
issues = report.get("issues", [])

c1, c2, c3, c4 = st.columns(4)
c1.metric("Packet status", packet.get("status", "unknown"))
c2.metric("Packet methods", packet.get("packet_method_count", 0))
c3.metric("Blockers", packet.get("blocker_count", 0))
c4.metric("Final approval", "Not recorded" if not safety.get("final_approval_recorded") else "CHECK")

if (
    safety.get("bridge_routing_network_transport_final_review_packet_only")
    and safety.get("final_review_packet_only")
    and safety.get("final_review_preview_created")
    and not safety.get("final_approval_recorded")
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
    st.success("Safe final review packet confirmed: no-write review only, bridge GET only, no approval, no execution, no transport, no bridge POST, no socket.")
else:
    st.error("Review final review packet safety flags before continuing.")

if packet.get("status") == "final_review_packet_blocked":
    st.error("Final review packet is blocked. Resolve blockers before future closure or implementation planning.")
elif packet.get("status") == "final_review_packet_review_required_no_write":
    st.warning("Final review packet has review items. This still does not authorize approvals, execution implementation, or network transport.")
else:
    st.success("Final review packet is ready for review. This still does not authorize approvals, execution implementation, or network transport.")

st.subheader("Final review packet summary")
st.json(packet)

st.subheader("Packet methods")
if methods:
    st.dataframe(methods, use_container_width=True, hide_index=True)
else:
    st.info("No packet methods were recorded.")

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
    st.success("No final review packet issues were recorded.")

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
    ("Download methods CSV", methods_csv_path, "phase20_bridge_routing_network_transport_final_review_packet_methods.csv"),
    ("Download checklist CSV", checklist_csv_path, "phase20_bridge_routing_network_transport_final_review_packet_checklist.csv"),
    ("Download artifacts CSV", artifacts_csv_path, "phase20_bridge_routing_network_transport_final_review_packet_artifacts.csv"),
    ("Download issues CSV", issues_csv_path, "phase20_bridge_routing_network_transport_final_review_packet_issues.csv"),
]:
    if path.exists():
        st.download_button(label, path.read_text(encoding="utf-8-sig"), filename, "text/csv")

st.download_button(
    "Download final review packet JSON",
    json.dumps(report, indent=2, default=str),
    "phase20_bridge_routing_network_transport_final_review_packet.json",
    "application/json",
)

with st.expander("Raw final review packet JSON"):
    st.json(report)
