from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import streamlit as st


st.set_page_config(page_title="Phase 20 Network Transport Artifact Gap Packet", page_icon="🧭", layout="wide")

WORKSPACE = Path(os.getenv("KPS_WORKSPACE", r"C:\Users\krist\Desktop\unified_pool_service_platform_build"))
BACKUP_DIR = WORKSPACE / "backups"


def latest_reports(limit: int = 20) -> list[Path]:
    if not BACKUP_DIR.exists():
        return []
    return sorted(
        [
            p
            for p in BACKUP_DIR.glob("phase21_phase20_network_transport_artifact_gap_packet_*")
            if p.is_dir() and (p / "phase21_phase20_network_transport_artifact_gap_packet.json").exists()
        ],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )[:limit]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


st.title("🧭 Phase 21 Step 4 - Phase 20 Network Transport Artifact Gap Packet")
st.caption("No-write artifact gap packet for the Phase 20 bridge routing network transport design chain.")

st.warning(
    "This page is Phase 20 network transport artifact-gap-only. It does not create design closure records, "
    "does not record final approvals, does not start an implementation phase, does not create execution implementation, "
    "does not call interface execution methods, does not add a real bridge HTTP client, does not add network transport, "
    "does not enable network transport, does not arm network transport, does not open network sockets, "
    "does not call bridge POST endpoints, does not create design-freeze records, does not record operator signoffs, "
    "does not create cutover packets, does not record cutover approvals, does not capture bridge responses, "
    "does not create response capture records, does not record operator approvals, does not create confirmation records, "
    "does not set environment variables, does not create rollback snapshots, does not create rollback rows, "
    "does not create audit rows, does not write to the bridge, does not save platform records, and does not call LACRM."
)

reports = latest_reports()
if not reports:
    st.info(
        "No Phase 20 network transport artifact gap packet found yet. Run "
        "`scripts\\phase21_generate_phase20_network_transport_artifact_gap_packet.ps1` from the platform repo."
    )
    st.stop()

choice = st.selectbox(
    "Artifact gap packet",
    options=list(range(len(reports))),
    format_func=lambda i: f"{reports[i].name} - {reports[i].stat().st_mtime_ns}",
)
report_dir = reports[choice]
json_path = report_dir / "phase21_phase20_network_transport_artifact_gap_packet.json"
gaps_csv_path = report_dir / "phase21_phase20_network_transport_artifact_gap_packet_gaps.csv"
regen_csv_path = report_dir / "phase21_phase20_network_transport_artifact_gap_packet_regeneration_order.csv"
sections_csv_path = report_dir / "phase21_phase20_network_transport_artifact_gap_packet_sections.csv"
buckets_csv_path = report_dir / "phase21_phase20_network_transport_artifact_gap_packet_buckets.csv"
artifacts_csv_path = report_dir / "phase21_phase20_network_transport_artifact_gap_packet_artifacts.csv"
source_csv_path = report_dir / "phase21_phase20_network_transport_artifact_gap_packet_source_audits.csv"
checklist_csv_path = report_dir / "phase21_phase20_network_transport_artifact_gap_packet_checklist.csv"
issues_csv_path = report_dir / "phase21_phase20_network_transport_artifact_gap_packet_issues.csv"
md_path = report_dir / "phase21_phase20_network_transport_artifact_gap_packet.md"

report = load_json(json_path)
safety = report.get("safety", {})
packet = report.get("artifact_gap_packet", {})
sections = report.get("sections", [])
buckets = report.get("buckets", [])
artifacts = report.get("artifacts", [])
source_audits = report.get("source_audits", [])
gaps = report.get("gaps", [])
regeneration_order = report.get("regeneration_order", [])
checklist = report.get("checklist", [])
issues = report.get("issues", [])

c1, c2, c3, c4 = st.columns(4)
c1.metric("Gap status", packet.get("status", "unknown"))
c2.metric("Missing artifacts", packet.get("missing_artifact_count", 0))
c3.metric("Gaps", packet.get("gap_count", 0))
c4.metric("Implementation phase", "Not started" if not safety.get("implementation_phase_started") else "CHECK")

if (
    safety.get("phase20_network_transport_artifact_gap_packet_only")
    and safety.get("artifact_gap_packet_only")
    and safety.get("bridge_get_only")
    and not safety.get("design_closure_record_created")
    and not safety.get("final_approval_recorded")
    and not safety.get("implementation_phase_started")
    and not safety.get("execution_implementation_created")
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
    st.success("Safe artifact gap packet confirmed: no-write review only, bridge GET only, no approval, no implementation phase, no transport, no bridge POST, no socket.")
else:
    st.error("Review artifact-gap safety flags before continuing.")

if packet.get("status") == "phase20_artifact_gap_packet_blocked":
    st.error("Artifact gap packet is blocked. Resolve blockers before further closeout work.")
elif packet.get("status") == "phase20_artifact_gap_packet_review_required_no_write":
    st.warning("Artifact gap packet has review items. This still does not authorize approvals, implementation, or network transport.")
else:
    st.success("Artifact gap packet is ready for review. This still does not authorize approvals, implementation, or network transport.")

st.subheader("Artifact gap summary")
st.json(packet)

st.subheader("Gaps")
if gaps:
    severity_values = sorted({str(row.get("severity") or "unknown") for row in gaps})
    selected_gap_severity = st.multiselect("Gap severity filter", severity_values, default=severity_values)
    filtered_gaps = [row for row in gaps if str(row.get("severity") or "unknown") in selected_gap_severity]
    st.dataframe(filtered_gaps, use_container_width=True, hide_index=True)
else:
    st.success("No gaps were recorded.")

st.subheader("Suggested regeneration order")
if regeneration_order:
    st.dataframe(regeneration_order, use_container_width=True, hide_index=True)
else:
    st.info("No regeneration order entries were recorded.")

st.subheader("Bucket summary")
if buckets:
    st.dataframe(buckets, use_container_width=True, hide_index=True)
else:
    st.info("No buckets were recorded.")

st.subheader("Indexed artifacts")
if artifacts:
    status_values = sorted({str(row.get("status") or "unknown") for row in artifacts})
    selected_statuses = st.multiselect("Artifact status filter", status_values, default=status_values)
    filtered_artifacts = [row for row in artifacts if str(row.get("status") or "unknown") in selected_statuses]
    st.dataframe(filtered_artifacts, use_container_width=True, hide_index=True)
else:
    st.info("No artifacts were recorded.")

st.subheader("Source audits")
if source_audits:
    st.dataframe(source_audits, use_container_width=True, hide_index=True)
else:
    st.info("No source audits were recorded.")

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
    st.success("No artifact-gap issues were recorded.")

st.subheader("Runtime status")
with st.expander("Runtime status"):
    st.json(report.get("runtime_status", {}))

st.subheader("Report files")
st.code(
    "\n".join(
        [
            f"Folder: {report_dir}",
            f"JSON: {json_path}",
            f"Gaps CSV: {gaps_csv_path}",
            f"Regeneration order CSV: {regen_csv_path}",
            f"Sections CSV: {sections_csv_path}",
            f"Buckets CSV: {buckets_csv_path}",
            f"Artifacts CSV: {artifacts_csv_path}",
            f"Source audits CSV: {source_csv_path}",
            f"Checklist CSV: {checklist_csv_path}",
            f"Issues CSV: {issues_csv_path}",
            f"Markdown: {md_path}",
        ]
    ),
    language="text",
)

for label, path, filename in [
    ("Download gaps CSV", gaps_csv_path, "phase21_phase20_network_transport_artifact_gap_packet_gaps.csv"),
    ("Download regeneration order CSV", regen_csv_path, "phase21_phase20_network_transport_artifact_gap_packet_regeneration_order.csv"),
    ("Download sections CSV", sections_csv_path, "phase21_phase20_network_transport_artifact_gap_packet_sections.csv"),
    ("Download buckets CSV", buckets_csv_path, "phase21_phase20_network_transport_artifact_gap_packet_buckets.csv"),
    ("Download artifacts CSV", artifacts_csv_path, "phase21_phase20_network_transport_artifact_gap_packet_artifacts.csv"),
    ("Download source audits CSV", source_csv_path, "phase21_phase20_network_transport_artifact_gap_packet_source_audits.csv"),
    ("Download checklist CSV", checklist_csv_path, "phase21_phase20_network_transport_artifact_gap_packet_checklist.csv"),
    ("Download issues CSV", issues_csv_path, "phase21_phase20_network_transport_artifact_gap_packet_issues.csv"),
]:
    if path.exists():
        st.download_button(label, path.read_text(encoding="utf-8-sig"), filename, "text/csv")

st.download_button(
    "Download artifact gap packet JSON",
    json.dumps(report, indent=2, default=str),
    "phase21_phase20_network_transport_artifact_gap_packet.json",
    "application/json",
)

with st.expander("Raw artifact gap packet JSON"):
    st.json(report)
