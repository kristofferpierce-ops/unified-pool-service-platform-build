from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import streamlit as st


st.set_page_config(page_title="Bridge Routing Rollback Snapshot", page_icon="🧯", layout="wide")

WORKSPACE = Path(os.getenv("KPS_WORKSPACE", r"C:\Users\krist\Desktop\unified_pool_service_platform_build"))
BACKUP_DIR = WORKSPACE / "backups"


def latest_snapshots(limit: int = 20) -> list[Path]:
    if not BACKUP_DIR.exists():
        return []
    return sorted(
        [
            p
            for p in BACKUP_DIR.glob("phase19_bridge_routing_rollback_snapshot_*")
            if p.is_dir() and (p / "phase19_bridge_routing_rollback_snapshot.json").exists()
        ],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )[:limit]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


st.title("🧯 Phase 19 Bridge Routing Rollback Snapshot")
st.caption("Read-only bridge GET snapshot for future rollback payload planning.")

st.warning(
    "This page is rollback-snapshot-only. It does not write to the bridge, does not save platform records, "
    "does not call bridge POST endpoints, and does not call LACRM."
)

snapshots = latest_snapshots()
if not snapshots:
    st.info(
        "No bridge routing rollback snapshot found yet. Run "
        "`scripts\\phase19_capture_bridge_routing_rollback_snapshot.ps1` from the platform repo."
    )
    st.stop()

choice = st.selectbox(
    "Rollback snapshot",
    options=list(range(len(snapshots))),
    format_func=lambda i: f"{snapshots[i].name} — {snapshots[i].stat().st_mtime_ns}",
)
snapshot_dir = snapshots[choice]
json_path = snapshot_dir / "phase19_bridge_routing_rollback_snapshot.json"
csv_path = snapshot_dir / "phase19_bridge_routing_rollback_snapshot.csv"
md_path = snapshot_dir / "phase19_bridge_routing_rollback_snapshot.md"

report = load_json(json_path)
safety = report.get("safety", {})
counts = report.get("counts", {})
rows = report.get("rollback_rows", [])
safety_errors = report.get("safety_errors", [])

c1, c2, c3, c4 = st.columns(4)
c1.metric("Bridge rules seen", counts.get("bridge_routing_rules_seen", 0))
c2.metric("Rollback rows", counts.get("rollback_rows", len(rows)))
c3.metric("Snapshot only", str(bool(safety.get("bridge_routing_rollback_snapshot_only"))))
c4.metric("Bridge POST", "Not called" if not safety.get("bridge_post_called") else "CHECK")

if (
    safety.get("bridge_routing_rollback_snapshot_only")
    and safety.get("bridge_get_only")
    and not safety.get("platform_db_mutation_performed")
    and not safety.get("bridge_post_called")
):
    st.success("Safe rollback snapshot confirmed: bridge GET only, no platform DB write, no bridge POST.")
else:
    st.error("Review rollback snapshot safety flags before continuing.")

if safety_errors:
    st.error("Safety errors were found.")
    st.code("\n".join(str(x) for x in safety_errors), language="text")
else:
    st.success("Rollback snapshot safety flags are clean.")

st.subheader("Bridge read status")
st.json(report.get("bridge_read_status", {}))

st.subheader("Rollback snapshot status summary")
st.json(counts.get("status_counts", {}))

st.subheader("Rollback rows")
if rows:
    status_values = sorted({str(row.get("rollback_snapshot_status") or "unknown") for row in rows})
    selected_statuses = st.multiselect("Status filter", status_values, default=status_values)
    filtered = [row for row in rows if str(row.get("rollback_snapshot_status") or "unknown") in selected_statuses]
    st.dataframe(filtered, use_container_width=True, hide_index=True)
else:
    st.info("No rollback rows were generated.")

st.subheader("Report files")
st.code(
    "\n".join(
        [
            f"Folder: {snapshot_dir}",
            f"JSON: {json_path}",
            f"CSV: {csv_path}",
            f"Markdown: {md_path}",
        ]
    ),
    language="text",
)

if csv_path.exists():
    st.download_button(
        "Download rollback snapshot CSV",
        csv_path.read_text(encoding="utf-8-sig"),
        "phase19_bridge_routing_rollback_snapshot.csv",
        "text/csv",
    )

st.download_button(
    "Download rollback snapshot JSON",
    json.dumps(report, indent=2, default=str),
    "phase19_bridge_routing_rollback_snapshot.json",
    "application/json",
)

with st.expander("Raw rollback snapshot JSON"):
    st.json(report)
