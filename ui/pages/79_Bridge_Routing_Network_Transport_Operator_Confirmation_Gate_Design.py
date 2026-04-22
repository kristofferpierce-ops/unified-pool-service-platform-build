from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import streamlit as st


st.set_page_config(page_title="Bridge Routing Network Transport Operator Confirmation Gate Design", page_icon="✍️", layout="wide")

WORKSPACE = Path(os.getenv("KPS_WORKSPACE", r"C:\Users\krist\Desktop\unified_pool_service_platform_build"))
BACKUP_DIR = WORKSPACE / "backups"


def latest_reports(limit: int = 20) -> list[Path]:
    if not BACKUP_DIR.exists():
        return []
    return sorted(
        [
            p
            for p in BACKUP_DIR.glob("phase20_bridge_routing_network_transport_operator_confirmation_gate_design_*")
            if p.is_dir() and (p / "phase20_bridge_routing_network_transport_operator_confirmation_gate_design.json").exists()
        ],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )[:limit]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


st.title("✍️ Phase 20 Bridge Routing Network Transport Operator Confirmation Gate Design")
st.caption("No-write operator confirmation gate design for future network transport work.")

st.warning(
    "This page is network-transport-operator-confirmation-gate-design-only. It does not record operator approvals, "
    "does not create confirmation records, does not set environment variables, does not create rollback snapshots, "
    "does not create rollback rows, does not create audit rows, does not write to the bridge, does not save platform records, "
    "does not call bridge POST endpoints, does not enable network transport, does not arm network transport, "
    "does not open network sockets, and does not call LACRM."
)

reports = latest_reports()
if not reports:
    st.info(
        "No bridge routing network transport operator confirmation gate design found yet. Run "
        "`scripts\\phase20_generate_bridge_routing_network_transport_operator_confirmation_gate_design.ps1` from the platform repo."
    )
    st.stop()

choice = st.selectbox(
    "Operator confirmation gate design report",
    options=list(range(len(reports))),
    format_func=lambda i: f"{reports[i].name} - {reports[i].stat().st_mtime_ns}",
)
report_dir = reports[choice]
json_path = report_dir / "phase20_bridge_routing_network_transport_operator_confirmation_gate_design.json"
requirements_csv_path = report_dir / "phase20_bridge_routing_network_transport_operator_confirmation_gate_design_requirements.csv"
artifacts_csv_path = report_dir / "phase20_bridge_routing_network_transport_operator_confirmation_gate_design_artifacts.csv"
gates_csv_path = report_dir / "phase20_bridge_routing_network_transport_operator_confirmation_gate_design_gates.csv"
issues_csv_path = report_dir / "phase20_bridge_routing_network_transport_operator_confirmation_gate_design_issues.csv"
md_path = report_dir / "phase20_bridge_routing_network_transport_operator_confirmation_gate_design.md"

report = load_json(json_path)
safety = report.get("safety", {})
gate = report.get("operator_confirmation_gate_design", {})
requirements = report.get("operator_confirmation_requirements", [])
artifacts = report.get("source_artifacts", [])
gates = report.get("gates", [])
issues = report.get("issues", [])

c1, c2, c3, c4 = st.columns(4)
c1.metric("Gate status", gate.get("status", "unknown"))
c2.metric("Requirements", gate.get("requirement_count", 0))
c3.metric("Blockers", gate.get("blocker_count", 0))
c4.metric("Operator approvals", "Not recorded" if not safety.get("operator_approval_recorded") else "CHECK")

if (
    safety.get("bridge_routing_network_transport_operator_confirmation_gate_design_only")
    and safety.get("bridge_get_only")
    and not safety.get("operator_approval_recorded")
    and not safety.get("confirmation_record_created")
    and not safety.get("environment_variables_set")
    and not safety.get("rollback_snapshot_created")
    and not safety.get("rollback_row_created")
    and not safety.get("audit_row_created")
    and not safety.get("platform_db_mutation_performed")
    and not safety.get("bridge_post_called")
    and not safety.get("network_transport_implemented")
    and not safety.get("network_socket_opened")
):
    st.success("Safe operator confirmation gate design confirmed: bridge GET only, no approvals, no env changes, no audit row, no bridge POST, no socket.")
else:
    st.error("Review operator confirmation gate safety flags before continuing.")

if gate.get("status") == "operator_confirmation_gate_design_blocked":
    st.error("Operator confirmation gate design is blocked. Resolve blockers before future real transport design.")
elif gate.get("status") == "operator_confirmation_gate_design_review_required_no_write":
    st.warning("Operator confirmation gate design has review items. This still does not authorize approvals or execution.")
else:
    st.success("Operator confirmation gate design is ready for review. This still does not authorize approvals or execution.")

st.subheader("Operator confirmation gate summary")
st.json(gate)

st.subheader("Future operator confirmation requirements")
if requirements:
    st.dataframe(requirements, use_container_width=True, hide_index=True)
else:
    st.info("No operator confirmation requirements were recorded.")

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
    st.success("No operator confirmation gate issues were recorded.")

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
    ("Download requirements CSV", requirements_csv_path, "phase20_bridge_routing_network_transport_operator_confirmation_gate_design_requirements.csv"),
    ("Download artifacts CSV", artifacts_csv_path, "phase20_bridge_routing_network_transport_operator_confirmation_gate_design_artifacts.csv"),
    ("Download gates CSV", gates_csv_path, "phase20_bridge_routing_network_transport_operator_confirmation_gate_design_gates.csv"),
    ("Download issues CSV", issues_csv_path, "phase20_bridge_routing_network_transport_operator_confirmation_gate_design_issues.csv"),
]:
    if path.exists():
        st.download_button(label, path.read_text(encoding="utf-8-sig"), filename, "text/csv")

st.download_button(
    "Download operator confirmation gate design JSON",
    json.dumps(report, indent=2, default=str),
    "phase20_bridge_routing_network_transport_operator_confirmation_gate_design.json",
    "application/json",
)

with st.expander("Raw operator confirmation gate design JSON"):
    st.json(report)
