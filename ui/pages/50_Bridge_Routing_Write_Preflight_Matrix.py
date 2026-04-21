from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import streamlit as st


st.set_page_config(page_title="Bridge Routing Write Preflight Matrix", page_icon="🧮", layout="wide")

WORKSPACE = Path(os.getenv("KPS_WORKSPACE", r"C:\Users\krist\Desktop\unified_pool_service_platform_build"))
BACKUP_DIR = WORKSPACE / "backups"


def latest_reports(limit: int = 20) -> list[Path]:
    if not BACKUP_DIR.exists():
        return []
    return sorted(
        [
            p
            for p in BACKUP_DIR.glob("phase19_bridge_routing_write_preflight_matrix_*")
            if p.is_dir() and (p / "phase19_bridge_routing_write_preflight_matrix.json").exists()
        ],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )[:limit]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


st.title("🧮 Phase 19 Bridge Routing Write Preflight Matrix")
st.caption("No-POST preflight matrix across dry-run validation, bundle rows, rollback snapshots, and runtime gates.")

st.warning(
    "This page is preflight-matrix-only. It does not write to the bridge, does not save platform records, "
    "does not call bridge POST endpoints, does not add a bridge HTTP client, and does not call LACRM."
)

reports = latest_reports()
if not reports:
    st.info(
        "No bridge routing write preflight matrix found yet. Run "
        "`scripts\\phase19_generate_bridge_routing_write_preflight_matrix.ps1` from the platform repo."
    )
    st.stop()

choice = st.selectbox(
    "Preflight matrix report",
    options=list(range(len(reports))),
    format_func=lambda i: f"{reports[i].name} - {reports[i].stat().st_mtime_ns}",
)
report_dir = reports[choice]
json_path = report_dir / "phase19_bridge_routing_write_preflight_matrix.json"
rows_csv_path = report_dir / "phase19_bridge_routing_write_preflight_matrix_rows.csv"
issues_csv_path = report_dir / "phase19_bridge_routing_write_preflight_matrix_issues.csv"
gates_csv_path = report_dir / "phase19_bridge_routing_write_preflight_matrix_global_gates.csv"
md_path = report_dir / "phase19_bridge_routing_write_preflight_matrix.md"

report = load_json(json_path)
safety = report.get("safety", {})
preflight = report.get("preflight", {})
issues = report.get("issues", [])
rows = report.get("preflight_rows", [])
global_gates = report.get("global_gates", [])

c1, c2, c3, c4 = st.columns(4)
c1.metric("Preflight status", preflight.get("status", "unknown"))
c2.metric("Blockers", preflight.get("blocker_count", 0))
c3.metric("Review items", preflight.get("review_count", 0))
c4.metric("Bridge POST", "Not called" if not safety.get("bridge_post_called") else "CHECK")

if (
    safety.get("bridge_routing_write_preflight_matrix_only")
    and safety.get("bridge_get_only")
    and not safety.get("platform_db_mutation_performed")
    and not safety.get("bridge_post_called")
    and not safety.get("bridge_http_client_implemented")
):
    st.success("Safe preflight matrix confirmed: bridge GET only, no platform DB write, no bridge POST, no HTTP client.")
else:
    st.error("Review preflight matrix safety flags before continuing.")

if preflight.get("status") == "blocked":
    st.error("Preflight matrix is blocked. Resolve blockers before any future bridge HTTP client design.")
elif preflight.get("status") == "preflight_valid_with_review_items":
    st.warning("Preflight matrix has review items. Resolve or accept them before future design.")
else:
    st.success("Preflight matrix has no hard blockers. This is still design-only and not executable.")

st.subheader("Preflight summary")
st.json(preflight)

st.subheader("Counts")
st.json(report.get("counts", {}))

st.subheader("Global gates")
if global_gates:
    category_values = sorted({str(row.get("source") or "unknown") for row in global_gates})
    selected_sources = st.multiselect("Gate source filter", category_values, default=category_values)
    filtered_gates = [row for row in global_gates if str(row.get("source") or "unknown") in selected_sources]
    st.dataframe(filtered_gates, use_container_width=True, hide_index=True)
else:
    st.info("No global gates were recorded.")

st.subheader("Preflight rows")
if rows:
    status_values = sorted({str(row.get("row_status") or "unknown") for row in rows})
    selected = st.multiselect("Row status filter", status_values, default=status_values)
    filtered = [row for row in rows if str(row.get("row_status") or "unknown") in selected]
    st.dataframe(filtered, use_container_width=True, hide_index=True)
else:
    st.info("No preflight rows were recorded.")

st.subheader("Issues")
if issues:
    severity_values = sorted({str(row.get("severity") or "unknown") for row in issues})
    selected_severity = st.multiselect("Severity filter", severity_values, default=severity_values)
    filtered_issues = [row for row in issues if str(row.get("severity") or "unknown") in selected_severity]
    st.dataframe(filtered_issues, use_container_width=True, hide_index=True)
else:
    st.success("No preflight issues were recorded.")

st.subheader("Platform status")
with st.expander("Platform status"):
    st.json(report.get("platform_status", {}))

st.subheader("Bridge status")
with st.expander("Bridge status"):
    st.json(report.get("bridge_status", {}))

st.subheader("Report files")
st.code(
    "\n".join(
        [
            f"Folder: {report_dir}",
            f"JSON: {json_path}",
            f"Rows CSV: {rows_csv_path}",
            f"Issues CSV: {issues_csv_path}",
            f"Global gates CSV: {gates_csv_path}",
            f"Markdown: {md_path}",
        ]
    ),
    language="text",
)

for label, path, filename in [
    ("Download preflight rows CSV", rows_csv_path, "phase19_bridge_routing_write_preflight_matrix_rows.csv"),
    ("Download preflight issues CSV", issues_csv_path, "phase19_bridge_routing_write_preflight_matrix_issues.csv"),
    ("Download global gates CSV", gates_csv_path, "phase19_bridge_routing_write_preflight_matrix_global_gates.csv"),
]:
    if path.exists():
        st.download_button(label, path.read_text(encoding="utf-8-sig"), filename, "text/csv")

st.download_button(
    "Download preflight matrix JSON",
    json.dumps(report, indent=2, default=str),
    "phase19_bridge_routing_write_preflight_matrix.json",
    "application/json",
)

with st.expander("Raw preflight matrix JSON"):
    st.json(report)
