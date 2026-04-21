from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import streamlit as st


st.set_page_config(page_title="Routing Candidate Import Check", page_icon="🔍", layout="wide")

WORKSPACE = Path(os.getenv("KPS_WORKSPACE", r"C:\Users\krist\Desktop\unified_pool_service_platform_build"))
BACKUP_DIR = WORKSPACE / "backups"


def latest_checks(limit: int = 20) -> list[Path]:
    if not BACKUP_DIR.exists():
        return []
    return sorted(
        [p for p in BACKUP_DIR.glob("phase19_routing_candidate_import_check_*") if p.is_dir()],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )[:limit]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


st.title("🔍 Phase 19 Routing Candidate Import Check")
st.caption("Dry-run comparison between the routing import plan and the platform candidate table.")

st.warning(
    "This page is dry-run-check-only. It does not import candidates, does not save routing rules, "
    "does not call bridge POST endpoints, and does not call LACRM."
)

checks = latest_checks()
if not checks:
    st.info(
        "No routing candidate import check found yet. Run "
        "`scripts\\phase19_check_routing_candidate_import.ps1` from the platform repo."
    )
    st.stop()

choice = st.selectbox(
    "Import check",
    options=list(range(len(checks))),
    format_func=lambda i: f"{checks[i].name} — {checks[i].stat().st_mtime_ns}",
)
check_dir = checks[choice]
json_path = check_dir / "phase19_routing_candidate_import_check.json"
csv_path = check_dir / "phase19_routing_candidate_import_check.csv"
md_path = check_dir / "phase19_routing_candidate_import_check.md"

report = load_json(json_path)
safety = report.get("safety", {})
counts = report.get("counts", {})
rows = report.get("check_rows", [])
api_safety_errors = report.get("api_safety_errors", [])

c1, c2, c3, c4 = st.columns(4)
c1.metric("Plan rows", counts.get("plan_rows", 0))
c2.metric("Existing candidates", counts.get("existing_candidates", 0))
c3.metric("Check rows", counts.get("check_rows", len(rows)))
c4.metric("Dry-run only", str(bool(safety.get("dry_run_check_only"))))

if safety.get("dry_run_check_only") and not safety.get("platform_db_mutation_performed") and not safety.get("candidate_import_performed"):
    st.success("Safe dry-run check confirmed: no platform DB write and no candidate import.")
else:
    st.error("Review import check safety flags before continuing.")

if api_safety_errors:
    st.error("Routing candidate API safety flags failed.")
    st.code("\n".join(str(x) for x in api_safety_errors), language="text")
else:
    st.success("Routing candidate API safety flags are read-only.")

st.subheader("Dry-run action summary")
st.json(counts.get("action_counts", {}))

st.subheader("Import check rows")
if rows:
    action_values = sorted({str(row.get("dry_run_action") or "unknown") for row in rows})
    selected_actions = st.multiselect("Dry-run action filter", action_values, default=action_values)
    filtered = [row for row in rows if str(row.get("dry_run_action") or "unknown") in selected_actions]
    st.dataframe(filtered, use_container_width=True, hide_index=True)
else:
    st.info("No import check rows were generated.")

st.subheader("API status")
st.json(report.get("api_status", {}))

st.subheader("Report files")
st.code(
    "\n".join(
        [
            f"Folder: {check_dir}",
            f"JSON: {json_path}",
            f"CSV: {csv_path}",
            f"Markdown: {md_path}",
        ]
    ),
    language="text",
)

if csv_path.exists():
    st.download_button(
        "Download import check CSV",
        csv_path.read_text(encoding="utf-8-sig"),
        "phase19_routing_candidate_import_check.csv",
        "text/csv",
    )

st.download_button(
    "Download import check JSON",
    json.dumps(report, indent=2, default=str),
    "phase19_routing_candidate_import_check.json",
    "application/json",
)

with st.expander("Raw import check JSON"):
    st.json(report)
