from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import streamlit as st


st.set_page_config(page_title="Bridge Routing Network Transport Dry Run Invocation Path Release Checkpoint", page_icon="🏁", layout="wide")

WORKSPACE = Path(os.getenv("KPS_WORKSPACE", r"C:\Users\krist\Desktop\unified_pool_service_platform_build"))
BACKUP_DIR = WORKSPACE / "backups"


def latest_reports(limit: int = 20) -> list[Path]:
    if not BACKUP_DIR.exists():
        return []
    return sorted(
        [
            p
            for p in BACKUP_DIR.glob("phase20_bridge_routing_network_transport_dry_run_invocation_path_release_checkpoint_*")
            if p.is_dir() and (p / "phase20_bridge_routing_network_transport_dry_run_invocation_path_release_checkpoint.json").exists()
        ],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )[:limit]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


st.title("🏁 Phase 20 Bridge Routing Network Transport Dry Run Invocation Path Release Checkpoint")
st.caption("No-socket release checkpoint across the Phase 20 dry-run invocation path evidence chain.")

st.warning(
    "This page is network-transport-dry-run-invocation-path-release-checkpoint-only. It does not write to the bridge, "
    "does not save platform records, does not call bridge POST endpoints, does not enable network transport, "
    "does not arm network transport, does not open network sockets, and does not call LACRM."
)

reports = latest_reports()
if not reports:
    st.info(
        "No bridge routing network transport dry-run invocation path release checkpoint found yet. Run "
        "`scripts\\phase20_generate_bridge_routing_network_transport_dry_run_invocation_path_release_checkpoint.ps1` from the platform repo."
    )
    st.stop()

choice = st.selectbox(
    "Dry-run invocation path release checkpoint",
    options=list(range(len(reports))),
    format_func=lambda i: f"{reports[i].name} - {reports[i].stat().st_mtime_ns}",
)
report_dir = reports[choice]
json_path = report_dir / "phase20_bridge_routing_network_transport_dry_run_invocation_path_release_checkpoint.json"
artifacts_csv_path = report_dir / "phase20_bridge_routing_network_transport_dry_run_invocation_path_release_checkpoint_artifacts.csv"
gates_csv_path = report_dir / "phase20_bridge_routing_network_transport_dry_run_invocation_path_release_checkpoint_gates.csv"
issues_csv_path = report_dir / "phase20_bridge_routing_network_transport_dry_run_invocation_path_release_checkpoint_issues.csv"
md_path = report_dir / "phase20_bridge_routing_network_transport_dry_run_invocation_path_release_checkpoint.md"

report = load_json(json_path)
safety = report.get("safety", {})
checkpoint = report.get("release_checkpoint", {})
artifacts = report.get("artifacts", [])
gates = report.get("gates", [])
issues = report.get("issues", [])

c1, c2, c3, c4 = st.columns(4)
c1.metric("Checkpoint status", checkpoint.get("status", "unknown"))
c2.metric("Artifacts", checkpoint.get("artifact_count", 0))
c3.metric("Blockers", checkpoint.get("blocker_count", 0))
c4.metric("Bridge POST", "Not called" if not safety.get("bridge_post_called") else "CHECK")

if (
    safety.get("bridge_routing_network_transport_dry_run_invocation_path_release_checkpoint_only")
    and safety.get("bridge_get_only")
    and not safety.get("platform_db_mutation_performed")
    and not safety.get("bridge_post_called")
    and not safety.get("network_transport_implemented")
    and not safety.get("network_socket_opened")
):
    st.success("Safe release checkpoint confirmed: bridge GET only, no platform DB write, no bridge POST, no socket.")
else:
    st.error("Review dry-run invocation path release checkpoint safety flags before continuing.")

if checkpoint.get("status") == "release_checkpoint_blocked":
    st.error("Dry-run invocation path release checkpoint is blocked. Resolve blockers before future real transport design.")
elif checkpoint.get("status") == "release_checkpoint_review_required_no_socket":
    st.warning("Dry-run invocation path release checkpoint has review items. This still does not authorize execution.")
else:
    st.success("Dry-run invocation path release checkpoint is clean for review. This still does not authorize execution.")

st.subheader("Release checkpoint summary")
st.json(checkpoint)

st.subheader("Artifacts with hashes")
if artifacts:
    st.dataframe(artifacts, use_container_width=True, hide_index=True)
else:
    st.info("No artifacts were recorded.")

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
    st.success("No release checkpoint issues were recorded.")

st.subheader("Runtime status")
with st.expander("Runtime status"):
    st.json(report.get("runtime_status", {}))

st.subheader("Report files")
st.code(
    "\n".join(
        [
            f"Folder: {report_dir}",
            f"JSON: {json_path}",
            f"Artifacts CSV: {artifacts_csv_path}",
            f"Gates CSV: {gates_csv_path}",
            f"Issues CSV: {issues_csv_path}",
            f"Markdown: {md_path}",
        ]
    ),
    language="text",
)

for label, path, filename in [
    ("Download artifacts CSV", artifacts_csv_path, "phase20_bridge_routing_network_transport_dry_run_invocation_path_release_checkpoint_artifacts.csv"),
    ("Download gates CSV", gates_csv_path, "phase20_bridge_routing_network_transport_dry_run_invocation_path_release_checkpoint_gates.csv"),
    ("Download issues CSV", issues_csv_path, "phase20_bridge_routing_network_transport_dry_run_invocation_path_release_checkpoint_issues.csv"),
]:
    if path.exists():
        st.download_button(label, path.read_text(encoding="utf-8-sig"), filename, "text/csv")

st.download_button(
    "Download dry-run invocation path release checkpoint JSON",
    json.dumps(report, indent=2, default=str),
    "phase20_bridge_routing_network_transport_dry_run_invocation_path_release_checkpoint.json",
    "application/json",
)

with st.expander("Raw dry-run invocation path release checkpoint JSON"):
    st.json(report)
