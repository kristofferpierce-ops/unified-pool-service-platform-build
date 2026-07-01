from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import streamlit as st


st.set_page_config(page_title="Phase 20 Network Transport Planning Entry Packet", page_icon="🧭", layout="wide")

WORKSPACE = Path(os.getenv("KPS_WORKSPACE", r"C:\Users\krist\Desktop\unified_pool_service_platform_build"))
BACKUP_DIR = WORKSPACE / "backups"


def latest_reports(limit: int = 20) -> list[Path]:
    if not BACKUP_DIR.exists():
        return []
    return sorted(
        [
            p
            for p in BACKUP_DIR.glob("phase22_phase20_network_transport_planning_entry_packet_*")
            if p.is_dir() and (p / "phase22_phase20_network_transport_planning_entry_packet.json").exists()
        ],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )[:limit]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


st.title("🧭 Phase 22 Step 1 - Phase 20 Network Transport Planning Entry Packet")
st.caption("No-write planning entry packet for the Phase 20 bridge routing network transport chain.")

st.warning(
    "This page is Phase 20 network transport planning-entry-only. It does not create design closure records, "
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
        "No Phase 20 network transport planning entry packet found yet. Run "
        "`scripts\\phase22_generate_phase20_network_transport_planning_entry_packet.ps1` from the platform repo."
    )
    st.stop()

choice = st.selectbox(
    "Planning entry packet",
    options=list(range(len(reports))),
    format_func=lambda i: f"{reports[i].name} - {reports[i].stat().st_mtime_ns}",
)
report_dir = reports[choice]
json_path = report_dir / "phase22_phase20_network_transport_planning_entry_packet.json"
sections_csv_path = report_dir / "phase22_phase20_network_transport_planning_entry_packet_sections.csv"
entries_csv_path = report_dir / "phase22_phase20_network_transport_planning_entry_packet_entries.csv"
decisions_csv_path = report_dir / "phase22_phase20_network_transport_planning_entry_packet_decisions.csv"
families_csv_path = report_dir / "phase22_phase20_network_transport_planning_entry_packet_artifact_families.csv"
git_status_csv_path = report_dir / "phase22_phase20_network_transport_planning_entry_packet_git_status.csv"
staged_csv_path = report_dir / "phase22_phase20_network_transport_planning_entry_packet_staged.csv"
source_artifacts_csv_path = report_dir / "phase22_phase20_network_transport_planning_entry_packet_source_artifacts.csv"
checklist_csv_path = report_dir / "phase22_phase20_network_transport_planning_entry_packet_checklist.csv"
issues_csv_path = report_dir / "phase22_phase20_network_transport_planning_entry_packet_issues.csv"
md_path = report_dir / "phase22_phase20_network_transport_planning_entry_packet.md"

report = load_json(json_path)
safety = report.get("safety", {})
packet = report.get("planning_entry_packet", {})
sections = report.get("planning_sections", [])
entries = report.get("planning_entries", [])
archive_decisions = report.get("archive_decisions", [])
artifact_families = report.get("artifact_families", [])
git_status_entries = report.get("git_status_entries", [])
staged_entries = report.get("staged_entries", [])
source_artifacts = report.get("source_artifacts", [])
checklist = report.get("checklist", [])
issues = report.get("issues", [])
planning_commands = report.get("planning_commands", [])

c1, c2, c3, c4 = st.columns(4)
c1.metric("Planning entry status", packet.get("status", "unknown"))
c2.metric("Archive decisions", packet.get("archive_decision_count", 0))
c3.metric("Review items", packet.get("review_count", 0))
c4.metric("Staged forbidden", packet.get("staged_forbidden_count", 0))

if (
    safety.get("phase20_network_transport_planning_entry_packet_only")
    and safety.get("planning_entry_only")
    and safety.get("planning_only")
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
    st.success("Safe planning entry confirmed: no-write planning only, bridge GET only, no approval, no implementation phase, no transport, no bridge POST, no socket.")
else:
    st.error("Review planning-entry safety flags before continuing.")

if packet.get("status") == "phase20_planning_entry_packet_blocked":
    st.error("Planning entry packet is blocked. Resolve blockers before continuing planning.")
elif packet.get("status") == "phase20_planning_entry_packet_review_required_no_write":
    st.warning("Planning entry packet has review items. This still does not authorize approvals, implementation, or network transport.")
else:
    st.success("Planning entry packet is ready for review. This still does not authorize approvals, implementation, or network transport.")

st.subheader("Planning entry summary")
st.json(packet)

st.subheader("Planning sections")
if sections:
    st.dataframe(sections, use_container_width=True, hide_index=True)
else:
    st.info("No planning sections were recorded.")

st.subheader("Planning entries")
if entries:
    category_values = sorted({str(row.get("category") or "unknown") for row in entries})
    selected_categories = st.multiselect("Entry category filter", category_values, default=category_values)
    filtered_entries = [row for row in entries if str(row.get("category") or "unknown") in selected_categories]
    st.dataframe(filtered_entries, use_container_width=True, hide_index=True)
else:
    st.info("No planning entries were recorded.")

st.subheader("Archive decisions")
if archive_decisions:
    decision_values = sorted({str(row.get("decision") or "unknown") for row in archive_decisions})
    selected_decisions = st.multiselect("Archive decision filter", decision_values, default=decision_values)
    filtered_decisions = [row for row in archive_decisions if str(row.get("decision") or "unknown") in selected_decisions]
    st.dataframe(filtered_decisions, use_container_width=True, hide_index=True)
else:
    st.info("No archive decisions were recorded.")

st.subheader("Artifact families")
if artifact_families:
    st.dataframe(artifact_families, use_container_width=True, hide_index=True)
else:
    st.info("No artifact families were recorded.")

st.subheader("Current git status classification")
if git_status_entries:
    category_values = sorted({str(row.get("category") or "unknown") for row in git_status_entries})
    selected_status_categories = st.multiselect("Git status category filter", category_values, default=category_values)
    filtered_git_status = [row for row in git_status_entries if str(row.get("category") or "unknown") in selected_status_categories]
    st.dataframe(filtered_git_status, use_container_width=True, hide_index=True)
else:
    st.info("No git status entries were recorded.")

st.subheader("Current staged set classification")
if staged_entries:
    st.dataframe(staged_entries, use_container_width=True, hide_index=True)
else:
    st.info("No staged entries were recorded yet.")

st.subheader("Source artifacts")
if source_artifacts:
    st.dataframe(source_artifacts, use_container_width=True, hide_index=True)
else:
    st.info("No source artifacts were recorded.")

st.subheader("Safe commit commands")
if planning_commands:
    st.code("\n".join(planning_commands), language="powershell")

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
    st.success("No planning-entry issues were recorded.")

st.subheader("Runtime status")
with st.expander("Runtime status"):
    st.json(report.get("runtime_status", {}))

st.subheader("Report files")
st.code(
    "\n".join(
        [
            f"Folder: {report_dir}",
            f"JSON: {json_path}",
            f"Sections CSV: {sections_csv_path}",
            f"Entries CSV: {entries_csv_path}",
            f"Decisions CSV: {decisions_csv_path}",
            f"Artifact families CSV: {families_csv_path}",
            f"Git status CSV: {git_status_csv_path}",
            f"Staged CSV: {staged_csv_path}",
            f"Source artifacts CSV: {source_artifacts_csv_path}",
            f"Checklist CSV: {checklist_csv_path}",
            f"Issues CSV: {issues_csv_path}",
            f"Markdown: {md_path}",
        ]
    ),
    language="text",
)

for label, path, filename in [
    ("Download sections CSV", sections_csv_path, "phase22_phase20_network_transport_planning_entry_packet_sections.csv"),
    ("Download entries CSV", entries_csv_path, "phase22_phase20_network_transport_planning_entry_packet_entries.csv"),
    ("Download decisions CSV", decisions_csv_path, "phase22_phase20_network_transport_planning_entry_packet_decisions.csv"),
    ("Download artifact families CSV", families_csv_path, "phase22_phase20_network_transport_planning_entry_packet_artifact_families.csv"),
    ("Download git status CSV", git_status_csv_path, "phase22_phase20_network_transport_planning_entry_packet_git_status.csv"),
    ("Download staged CSV", staged_csv_path, "phase22_phase20_network_transport_planning_entry_packet_staged.csv"),
    ("Download source artifacts CSV", source_artifacts_csv_path, "phase22_phase20_network_transport_planning_entry_packet_source_artifacts.csv"),
    ("Download checklist CSV", checklist_csv_path, "phase22_phase20_network_transport_planning_entry_packet_checklist.csv"),
    ("Download issues CSV", issues_csv_path, "phase22_phase20_network_transport_planning_entry_packet_issues.csv"),
]:
    if path.exists():
        st.download_button(label, path.read_text(encoding="utf-8-sig"), filename, "text/csv")

st.download_button(
    "Download planning entry packet JSON",
    json.dumps(report, indent=2, default=str),
    "phase22_phase20_network_transport_planning_entry_packet.json",
    "application/json",
)

with st.expander("Raw planning entry packet JSON"):
    st.json(report)
