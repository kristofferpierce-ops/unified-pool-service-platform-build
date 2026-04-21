from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import requests
import streamlit as st


st.set_page_config(page_title="Bridge Routing Write Audit Writer", page_icon="✍️", layout="wide")

WORKSPACE = Path(os.getenv("KPS_WORKSPACE", r"C:\Users\krist\Desktop\unified_pool_service_platform_build"))
BACKUP_DIR = WORKSPACE / "backups"
PLATFORM_API = os.getenv("PLATFORM_API_BASE_URL", "http://127.0.0.1:8010")


def get_json(url: str) -> tuple[bool, Any]:
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return True, response.json()
    except Exception as exc:  # pragma: no cover - runtime display
        return False, str(exc)


def latest_runs(limit: int = 20) -> list[Path]:
    if not BACKUP_DIR.exists():
        return []
    return sorted(
        [
            p
            for p in BACKUP_DIR.glob("phase19_bridge_routing_write_audit_writer_run_*")
            if p.is_dir() and (p / "phase19_bridge_routing_write_audit_writer_run.json").exists()
        ],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )[:limit]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


st.title("✍️ Phase 19 Bridge Routing Write Audit Writer")
st.caption("Disabled-by-default platform-local audit-row writer. Dry-run is the safe default.")

st.warning(
    "This page is status/report only. It does not trigger audit writes, does not write to the bridge, "
    "does not call bridge POST endpoints, and does not call LACRM."
)

status_ok, status = get_json(f"{PLATFORM_API}/front-desk/routing/bridge-write-audit-writer/status")
if not status_ok:
    st.error(f"Could not read bridge routing audit writer status: {status}")
    st.stop()

c1, c2, c3, c4 = st.columns(4)
c1.metric("Safe default", status.get("safe_default", "unknown"))
c2.metric("Audit write enabled", str(bool(status.get("audit_write_enabled"))))
c3.metric("Audit write armed", str(bool(status.get("audit_write_armed"))))
c4.metric("Bridge POST implemented", str(bool(status.get("bridge_post_call_implemented"))))

if not status.get("audit_write_enabled") and not status.get("audit_write_armed") and not status.get("bridge_post_call_implemented"):
    st.success("Safe default confirmed: audit writer disabled, unarmed, and no bridge POST implementation.")
else:
    st.warning("Audit writer gates are not fully disabled. Confirm this is intentional before running any execute flow.")

st.subheader("Audit writer gate status")
st.json(status)

st.subheader("How to run safe dry-run")
st.code(
    "powershell -ExecutionPolicy Bypass -File scripts\\phase19_run_bridge_routing_write_audit_writer.ps1",
    language="powershell",
)

st.subheader("Generated writer runs")
runs = latest_runs()
if not runs:
    st.info("No bridge routing audit writer run reports found yet.")
else:
    choice = st.selectbox(
        "Audit writer run",
        options=list(range(len(runs))),
        format_func=lambda i: f"{runs[i].name} — {runs[i].stat().st_mtime_ns}",
    )
    run_dir = runs[choice]
    json_path = run_dir / "phase19_bridge_routing_write_audit_writer_run.json"
    csv_path = run_dir / "phase19_bridge_routing_write_audit_writer_run.csv"
    report = load_json(json_path)

    st.json(report.get("safety", {}))
    st.subheader("Action counts")
    st.json(report.get("counts", {}).get("action_counts", {}))

    rows = report.get("write_rows", [])
    if rows:
        st.dataframe(rows, use_container_width=True, hide_index=True)

    if csv_path.exists():
        st.download_button(
            "Download audit writer run CSV",
            csv_path.read_text(encoding="utf-8-sig"),
            "phase19_bridge_routing_write_audit_writer_run.csv",
            "text/csv",
        )

    st.download_button(
        "Download audit writer run JSON",
        json.dumps(report, indent=2, default=str),
        "phase19_bridge_routing_write_audit_writer_run.json",
        "application/json",
    )
