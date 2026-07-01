from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import streamlit as st


st.set_page_config(page_title="Bridge Routing Network Transport Preflight Matrix", page_icon="🧮", layout="wide")

WORKSPACE = Path(os.getenv("KPS_WORKSPACE", r"C:\Users\krist\Desktop\unified_pool_service_platform_build"))
BACKUP_DIR = WORKSPACE / "backups"


def latest_reports(limit: int = 20) -> list[Path]:
    if not BACKUP_DIR.exists():
        return []
    return sorted(
        [
            p
            for p in BACKUP_DIR.glob("phase20_bridge_routing_network_transport_preflight_matrix_*")
            if p.is_dir() and (p / "phase20_bridge_routing_network_transport_preflight_matrix.json").exists()
        ],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )[:limit]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


st.title("🧮 Phase 20 Bridge Routing Network Transport Preflight Matrix")
st.caption("No-socket preflight matrix for the bridge routing network transport dry-run adapter path.")

st.warning(
    "This page is network-transport-preflight-matrix-only. It does not write to the bridge, does not save platform records, "
    "does not call bridge POST endpoints, does not enable network transport, does not arm network transport, "
    "does not open network sockets, and does not call LACRM."
)

reports = latest_reports()
if not reports:
    st.info(
        "No bridge routing network transport preflight matrix found yet. Run "
        "`scripts\\phase20_generate_bridge_routing_network_transport_preflight_matrix.ps1` from the platform repo."
    )
    st.stop()

choice = st.selectbox(
    "Network transport preflight matrix",
    options=list(range(len(reports))),
    format_func=lambda i: f"{reports[i].name} - {reports[i].stat().st_mtime_ns}",
)
report_dir = reports[choice]
json_path = report_dir / "phase20_bridge_routing_network_transport_preflight_matrix.json"
gates_csv_path = report_dir / "phase20_bridge_routing_network_transport_preflight_matrix_global_gates.csv"
rows_csv_path = report_dir / "phase20_bridge_routing_network_transport_preflight_matrix_rows.csv"
issues_csv_path = report_dir / "phase20_bridge_routing_network_transport_preflight_matrix_issues.csv"
md_path = report_dir / "phase20_bridge_routing_network_transport_preflight_matrix.md"

report = load_json(json_path)
safety = report.get("safety", {})
preflight = report.get("preflight", {})
gates = report.get("global_gates", [])
rows = report.get("transport_rows", [])
issues = report.get("issues", [])

c1, c2, c3, c4 = st.columns(4)
c1.metric("Preflight status", preflight.get("status", "unknown"))
c2.metric("Blockers", preflight.get("blocker_count", 0))
c3.metric("Review items", preflight.get("review_count", 0))
c4.metric("Bridge POST", "Not called" if not safety.get("bridge_post_called") else "CHECK")

if (
    safety.get("bridge_routing_network_transport_preflight_matrix_only")
    and safety.get("bridge_get_only")
    and not safety.get("platform_db_mutation_performed")
    and not safety.get("bridge_post_called")
    and not safety.get("network_transport_implemented")
    and not safety.get("network_socket_opened")
):
    st.success("Safe preflight matrix confirmed: bridge GET only, no platform DB write, no bridge POST, no socket.")
else:
    st.error("Review network transport preflight safety flags before continuing.")

if preflight.get("status") == "blocked":
    st.error("Network transport preflight matrix is blocked. Resolve blockers before future real transport design.")
elif preflight.get("status") == "preflight_valid_with_review_items":
    st.warning("Network transport preflight matrix has review items. This still does not authorize execution.")
else:
    st.success("Network transport preflight matrix is valid for design review. This still does not authorize execution.")

st.subheader("Preflight summary")
st.json(preflight)

st.subheader("Transport rows")
if rows:
    status_values = sorted({str(row.get("row_status") or "unknown") for row in rows})
    selected_statuses = st.multiselect("Row status filter", status_values, default=status_values)
    filtered_rows = [row for row in rows if str(row.get("row_status") or "unknown") in selected_statuses]
    st.dataframe(filtered_rows, use_container_width=True, hide_index=True)
else:
    st.info("No transport rows were recorded.")

st.subheader("Global gates")
if gates:
    severity_values = sorted({str(row.get("severity") or "unknown") for row in gates})
    selected_gate_severity = st.multiselect("Gate severity filter", severity_values, default=severity_values)
    filtered_gates = [row for row in gates if str(row.get("severity") or "unknown") in selected_gate_severity]
    st.dataframe(filtered_gates, use_container_width=True, hide_index=True)
else:
    st.info("No global gates were recorded.")

st.subheader("Issues")
if issues:
    severity_values = sorted({str(row.get("severity") or "unknown") for row in issues})
    selected_issue_severity = st.multiselect("Issue severity filter", severity_values, default=severity_values)
    filtered_issues = [row for row in issues if str(row.get("severity") or "unknown") in selected_issue_severity]
    st.dataframe(filtered_issues, use_container_width=True, hide_index=True)
else:
    st.success("No preflight issues were recorded.")

st.subheader("Runtime status")
with st.expander("Runtime status"):
    st.json(report.get("runtime_status", {}))

st.subheader("Report files")
st.code(
    "\n".join(
        [
            f"Folder: {report_dir}",
            f"JSON: {json_path}",
            f"Global gates CSV: {gates_csv_path}",
            f"Rows CSV: {rows_csv_path}",
            f"Issues CSV: {issues_csv_path}",
            f"Markdown: {md_path}",
        ]
    ),
    language="text",
)

for label, path, filename in [
    ("Download global gates CSV", gates_csv_path, "phase20_bridge_routing_network_transport_preflight_matrix_global_gates.csv"),
    ("Download transport rows CSV", rows_csv_path, "phase20_bridge_routing_network_transport_preflight_matrix_rows.csv"),
    ("Download issues CSV", issues_csv_path, "phase20_bridge_routing_network_transport_preflight_matrix_issues.csv"),
]:
    if path.exists():
        st.download_button(label, path.read_text(encoding="utf-8-sig"), filename, "text/csv")

st.download_button(
    "Download network transport preflight matrix JSON",
    json.dumps(report, indent=2, default=str),
    "phase20_bridge_routing_network_transport_preflight_matrix.json",
    "application/json",
)

with st.expander("Raw network transport preflight matrix JSON"):
    st.json(report)
