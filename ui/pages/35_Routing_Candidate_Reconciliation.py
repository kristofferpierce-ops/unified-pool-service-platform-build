from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import streamlit as st


st.set_page_config(page_title="Routing Candidate Reconciliation", page_icon="🧾", layout="wide")

WORKSPACE = Path(os.getenv("KPS_WORKSPACE", r"C:\Users\krist\Desktop\unified_pool_service_platform_build"))
BACKUP_DIR = WORKSPACE / "backups"


def latest_reports(limit: int = 20) -> list[Path]:
    if not BACKUP_DIR.exists():
        return []
    return sorted(
        [p for p in BACKUP_DIR.glob("phase19_routing_candidate_reconciliation_*") if p.is_dir()],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )[:limit]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


st.title("🧾 Phase 19 Routing Candidate Reconciliation")
st.caption("Read-only comparison between bridge routing snapshot keys and platform routing candidates.")

st.warning(
    "This page is reconciliation-only. It does not save candidate decisions, does not save routing rules, "
    "does not call bridge POST endpoints, and does not call LACRM."
)

reports = latest_reports()
if not reports:
    st.info(
        "No routing candidate reconciliation report found yet. Run "
        "`scripts\\phase19_reconcile_routing_candidates.ps1` from the platform repo."
    )
    st.stop()

choice = st.selectbox(
    "Reconciliation report",
    options=list(range(len(reports))),
    format_func=lambda i: f"{reports[i].name} — {reports[i].stat().st_mtime_ns}",
)
report_dir = reports[choice]
json_path = report_dir / "phase19_routing_candidate_reconciliation.json"
csv_path = report_dir / "phase19_routing_candidate_reconciliation.csv"
md_path = report_dir / "phase19_routing_candidate_reconciliation.md"

report = load_json(json_path)
safety = report.get("safety", {})
counts = report.get("counts", {})
rows = report.get("reconciliation_rows", [])
safety_errors = report.get("safety_errors", [])

c1, c2, c3, c4 = st.columns(4)
c1.metric("Bridge keys", counts.get("bridge_unique_keys", 0))
c2.metric("Candidate keys", counts.get("platform_candidate_keys", 0))
c3.metric("Rows", counts.get("reconciliation_rows", len(rows)))
c4.metric("Reconciliation only", str(bool(safety.get("reconciliation_only"))))

if safety.get("reconciliation_only") and not safety.get("platform_db_mutation_performed") and not safety.get("bridge_mutation_performed"):
    st.success("Safe reconciliation confirmed: no platform DB write and no bridge mutation.")
else:
    st.error("Review reconciliation safety flags before continuing.")

if safety_errors:
    st.error("Safety errors were found.")
    st.code("\n".join(str(x) for x in safety_errors), language="text")
else:
    st.success("Candidate/workbench safety flags are read-only.")

st.subheader("Reconciliation status summary")
st.json(counts.get("status_counts", {}))

st.subheader("Severity summary")
st.json(counts.get("severity_counts", {}))

st.subheader("Reconciliation rows")
if rows:
    severity_values = sorted({str(row.get("severity") or "unknown") for row in rows})
    selected_severities = st.multiselect("Severity filter", severity_values, default=severity_values)

    status_values = sorted({str(row.get("reconciliation_status") or "unknown") for row in rows})
    selected_statuses = st.multiselect("Status filter", status_values, default=status_values)

    filtered = [
        row for row in rows
        if str(row.get("severity") or "unknown") in selected_severities
        and str(row.get("reconciliation_status") or "unknown") in selected_statuses
    ]
    st.dataframe(filtered, use_container_width=True, hide_index=True)
else:
    st.info("No reconciliation rows were generated.")

st.subheader("Report files")
st.code(
    "\n".join(
        [
            f"Folder: {report_dir}",
            f"JSON: {json_path}",
            f"CSV: {csv_path}",
            f"Markdown: {md_path}",
        ]
    ),
    language="text",
)

if csv_path.exists():
    st.download_button(
        "Download reconciliation CSV",
        csv_path.read_text(encoding="utf-8-sig"),
        "phase19_routing_candidate_reconciliation.csv",
        "text/csv",
    )

st.download_button(
    "Download reconciliation JSON",
    json.dumps(report, indent=2, default=str),
    "phase19_routing_candidate_reconciliation.json",
    "application/json",
)

with st.expander("Raw reconciliation JSON"):
    st.json(report)
