from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import streamlit as st


st.set_page_config(page_title="Bridge Routing Write Readiness", page_icon="✅", layout="wide")

WORKSPACE = Path(os.getenv("KPS_WORKSPACE", r"C:\Users\krist\Desktop\unified_pool_service_platform_build"))
BACKUP_DIR = WORKSPACE / "backups"


def latest_reports(limit: int = 20) -> list[Path]:
    if not BACKUP_DIR.exists():
        return []
    return sorted(
        [
            p
            for p in BACKUP_DIR.glob("phase19_bridge_routing_write_readiness_*")
            if p.is_dir() and (p / "phase19_bridge_routing_write_readiness.json").exists()
        ],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )[:limit]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


st.title("✅ Phase 19 Bridge Routing Write Readiness")
st.caption("Go/no-go gate across contract, preview, rehearsal, audit plan, audit writer dry-run, and rollback snapshot.")

st.warning(
    "This page is readiness-only. It does not write to the bridge, does not save platform records, "
    "does not call bridge POST endpoints, and does not call LACRM."
)

reports = latest_reports()
if not reports:
    st.info(
        "No bridge routing write readiness report found yet. Run "
        "`scripts\\phase19_check_bridge_routing_write_readiness.ps1` from the platform repo."
    )
    st.stop()

choice = st.selectbox(
    "Readiness report",
    options=list(range(len(reports))),
    format_func=lambda i: f"{reports[i].name} — {reports[i].stat().st_mtime_ns}",
)
report_dir = reports[choice]
json_path = report_dir / "phase19_bridge_routing_write_readiness.json"
blockers_csv_path = report_dir / "phase19_bridge_routing_write_readiness_blockers.csv"
artifacts_csv_path = report_dir / "phase19_bridge_routing_write_readiness_artifacts.csv"
md_path = report_dir / "phase19_bridge_routing_write_readiness.md"

report = load_json(json_path)
safety = report.get("safety", {})
readiness = report.get("readiness", {})
counts = report.get("counts", {})
blockers = report.get("blockers", [])
artifacts = report.get("artifacts", [])

c1, c2, c3, c4 = st.columns(4)
c1.metric("Go/no-go", readiness.get("go_no_go", "unknown"))
c2.metric("Blockers", readiness.get("blocker_count", 0))
c3.metric("Review items", readiness.get("review_count", 0))
c4.metric("Bridge POST", "Not called" if not safety.get("bridge_post_called") else "CHECK")

if (
    safety.get("bridge_routing_write_readiness_only")
    and not safety.get("platform_db_mutation_performed")
    and not safety.get("bridge_post_called")
):
    st.success("Safe readiness report confirmed: no platform DB write, no bridge POST, no LACRM call.")
else:
    st.error("Review readiness safety flags before continuing.")

if readiness.get("go_no_go") == "blocked":
    st.error("Readiness is blocked. Resolve blockers before any future bridge-write implementation.")
elif readiness.get("go_no_go") == "review_required_before_future_write_design":
    st.warning("No hard blockers, but review items remain before future write design.")
else:
    st.success("Ready for future guarded-write design review. This still does not allow execution.")

st.subheader("Readiness summary")
st.json(readiness)

st.subheader("Counts")
st.json(counts)

st.subheader("Artifacts")
if artifacts:
    st.dataframe(artifacts, use_container_width=True, hide_index=True)
else:
    st.info("No artifacts were recorded.")

st.subheader("Blockers / review items")
if blockers:
    severity_values = sorted({str(row.get("severity") or "unknown") for row in blockers})
    selected = st.multiselect("Severity filter", severity_values, default=severity_values)
    filtered = [row for row in blockers if str(row.get("severity") or "unknown") in selected]
    st.dataframe(filtered, use_container_width=True, hide_index=True)
else:
    st.success("No blockers or review items were recorded.")

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
            f"Blockers CSV: {blockers_csv_path}",
            f"Artifacts CSV: {artifacts_csv_path}",
            f"Markdown: {md_path}",
        ]
    ),
    language="text",
)

if blockers_csv_path.exists():
    st.download_button(
        "Download blockers CSV",
        blockers_csv_path.read_text(encoding="utf-8-sig"),
        "phase19_bridge_routing_write_readiness_blockers.csv",
        "text/csv",
    )

if artifacts_csv_path.exists():
    st.download_button(
        "Download artifacts CSV",
        artifacts_csv_path.read_text(encoding="utf-8-sig"),
        "phase19_bridge_routing_write_readiness_artifacts.csv",
        "text/csv",
    )

st.download_button(
    "Download readiness JSON",
    json.dumps(report, indent=2, default=str),
    "phase19_bridge_routing_write_readiness.json",
    "application/json",
)

with st.expander("Raw readiness JSON"):
    st.json(report)
