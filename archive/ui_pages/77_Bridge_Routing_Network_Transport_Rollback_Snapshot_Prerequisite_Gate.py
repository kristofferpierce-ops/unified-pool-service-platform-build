from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import streamlit as st


st.set_page_config(page_title="Bridge Routing Network Transport Rollback Snapshot Prerequisite Gate", page_icon="🧯", layout="wide")

WORKSPACE = Path(os.getenv("KPS_WORKSPACE", r"C:\Users\krist\Desktop\unified_pool_service_platform_build"))
BACKUP_DIR = WORKSPACE / "backups"


def latest_reports(limit: int = 20) -> list[Path]:
    if not BACKUP_DIR.exists():
        return []
    return sorted(
        [
            p
            for p in BACKUP_DIR.glob("phase20_bridge_routing_network_transport_rollback_snapshot_prerequisite_gate_*")
            if p.is_dir() and (p / "phase20_bridge_routing_network_transport_rollback_snapshot_prerequisite_gate.json").exists()
        ],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )[:limit]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


st.title("🧯 Phase 20 Bridge Routing Network Transport Rollback Snapshot Prerequisite Gate")
st.caption("No-write rollback snapshot prerequisite gate for future network transport design.")

st.warning(
    "This page is network-transport-rollback-snapshot-prerequisite-gate-only. It does not create rollback snapshots, "
    "does not create rollback rows, does not create audit rows, does not write to the bridge, does not save platform records, "
    "does not call bridge POST endpoints, does not enable network transport, does not arm network transport, "
    "does not open network sockets, and does not call LACRM."
)

reports = latest_reports()
if not reports:
    st.info(
        "No bridge routing network transport rollback snapshot prerequisite gate found yet. Run "
        "`scripts\\phase20_generate_bridge_routing_network_transport_rollback_snapshot_prerequisite_gate.ps1` from the platform repo."
    )
    st.stop()

choice = st.selectbox(
    "Rollback snapshot prerequisite gate report",
    options=list(range(len(reports))),
    format_func=lambda i: f"{reports[i].name} - {reports[i].stat().st_mtime_ns}",
)
report_dir = reports[choice]
json_path = report_dir / "phase20_bridge_routing_network_transport_rollback_snapshot_prerequisite_gate.json"
requirements_csv_path = report_dir / "phase20_bridge_routing_network_transport_rollback_snapshot_prerequisite_gate_requirements.csv"
artifacts_csv_path = report_dir / "phase20_bridge_routing_network_transport_rollback_snapshot_prerequisite_gate_artifacts.csv"
gates_csv_path = report_dir / "phase20_bridge_routing_network_transport_rollback_snapshot_prerequisite_gate_gates.csv"
issues_csv_path = report_dir / "phase20_bridge_routing_network_transport_rollback_snapshot_prerequisite_gate_issues.csv"
md_path = report_dir / "phase20_bridge_routing_network_transport_rollback_snapshot_prerequisite_gate.md"

report = load_json(json_path)
safety = report.get("safety", {})
gate = report.get("rollback_snapshot_prerequisite_gate", {})
requirements = report.get("rollback_requirements", [])
artifacts = report.get("source_artifacts", [])
gates = report.get("gates", [])
issues = report.get("issues", [])

c1, c2, c3, c4 = st.columns(4)
c1.metric("Gate status", gate.get("status", "unknown"))
c2.metric("Requirements", gate.get("requirement_count", 0))
c3.metric("Blockers", gate.get("blocker_count", 0))
c4.metric("Rollback snapshots", "Not created" if not safety.get("rollback_snapshot_created") else "CHECK")

if (
    safety.get("bridge_routing_network_transport_rollback_snapshot_prerequisite_gate_only")
    and safety.get("bridge_get_only")
    and not safety.get("rollback_snapshot_created")
    and not safety.get("rollback_row_created")
    and not safety.get("audit_row_created")
    and not safety.get("platform_db_mutation_performed")
    and not safety.get("bridge_post_called")
    and not safety.get("network_transport_implemented")
    and not safety.get("network_socket_opened")
):
    st.success("Safe rollback prerequisite gate confirmed: bridge GET only, no rollback snapshot, no audit row, no bridge POST, no socket.")
else:
    st.error("Review rollback snapshot prerequisite gate safety flags before continuing.")

if gate.get("status") == "rollback_snapshot_prerequisite_blocked":
    st.error("Rollback snapshot prerequisite gate is blocked. Resolve blockers before future real transport design.")
elif gate.get("status") == "rollback_snapshot_prerequisite_review_required_no_write":
    st.warning("Rollback snapshot prerequisite gate has review items. This still does not authorize execution or rollback-row writes.")
else:
    st.success("Rollback snapshot prerequisite gate is ready for review. This still does not authorize execution or rollback-row writes.")

st.subheader("Rollback snapshot prerequisite summary")
st.json(gate)

st.subheader("Future rollback requirements")
if requirements:
    st.dataframe(requirements, use_container_width=True, hide_index=True)
else:
    st.info("No rollback requirements were recorded.")

st.subheader("Source artifacts")
if artifacts:
    st.dataframe(artifacts, use_container_width=True, hide_index=True)
else:
    st.info("No source artifacts were recorded.")

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
    st.success("No rollback prerequisite issues were recorded.")

st.subheader("Runtime status")
with st.expander("Runtime status"):
    st.json(report.get("runtime_status", {}))

st.subheader("Report files")
st.code(
    "\n".join(
        [
            f"Folder: {report_dir}",
            f"JSON: {json_path}",
            f"Requirements CSV: {requirements_csv_path}",
            f"Artifacts CSV: {artifacts_csv_path}",
            f"Gates CSV: {gates_csv_path}",
            f"Issues CSV: {issues_csv_path}",
            f"Markdown: {md_path}",
        ]
    ),
    language="text",
)

for label, path, filename in [
    ("Download requirements CSV", requirements_csv_path, "phase20_bridge_routing_network_transport_rollback_snapshot_prerequisite_gate_requirements.csv"),
    ("Download artifacts CSV", artifacts_csv_path, "phase20_bridge_routing_network_transport_rollback_snapshot_prerequisite_gate_artifacts.csv"),
    ("Download gates CSV", gates_csv_path, "phase20_bridge_routing_network_transport_rollback_snapshot_prerequisite_gate_gates.csv"),
    ("Download issues CSV", issues_csv_path, "phase20_bridge_routing_network_transport_rollback_snapshot_prerequisite_gate_issues.csv"),
]:
    if path.exists():
        st.download_button(label, path.read_text(encoding="utf-8-sig"), filename, "text/csv")

st.download_button(
    "Download rollback snapshot prerequisite gate JSON",
    json.dumps(report, indent=2, default=str),
    "phase20_bridge_routing_network_transport_rollback_snapshot_prerequisite_gate.json",
    "application/json",
)

with st.expander("Raw rollback snapshot prerequisite gate JSON"):
    st.json(report)
