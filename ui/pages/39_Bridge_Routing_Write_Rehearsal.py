from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import requests
import streamlit as st


st.set_page_config(page_title="Bridge Routing Write Rehearsal", page_icon="🚧", layout="wide")

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


def latest_reports(limit: int = 20) -> list[Path]:
    if not BACKUP_DIR.exists():
        return []
    return sorted(
        [p for p in BACKUP_DIR.glob("phase19_bridge_routing_write_rehearsal_*") if p.is_dir()],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )[:limit]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


st.title("🚧 Phase 19 Bridge Routing Write Rehearsal")
st.caption("Guarded bridge routing write rehearsal. Blocked by default; no bridge POST is implemented.")

st.warning(
    "This page is report/status only. It does not trigger rehearsals, does not write to the bridge, "
    "does not save platform records, does not call bridge POST endpoints, and does not call LACRM."
)

status_ok, status = get_json(f"{PLATFORM_API}/front-desk/routing/bridge-write-rehearsal/status")
if not status_ok:
    st.error(f"Could not read bridge routing write rehearsal status: {status}")
    st.stop()

c1, c2, c3, c4 = st.columns(4)
c1.metric("Safe default", status.get("safe_default", "unknown"))
c2.metric("Write enabled", str(bool(status.get("bridge_routing_write_enabled"))))
c3.metric("Write armed", str(bool(status.get("bridge_routing_write_armed"))))
c4.metric("Bridge POST implemented", str(bool(status.get("bridge_post_call_implemented"))))

if status.get("rehearsal_only") and not status.get("bridge_post_call_implemented") and not status.get("bridge_post_called"):
    st.success("Safe rehearsal status confirmed: bridge POST is not implemented and has not been called.")
else:
    st.error("Review bridge write rehearsal safety flags before continuing.")

st.subheader("Rehearsal status")
st.json(status)

st.subheader("How to run safe rehearsal")
st.code(
    "powershell -ExecutionPolicy Bypass -File scripts\\phase19_run_bridge_routing_write_rehearsal.ps1",
    language="powershell",
)

st.subheader("Generated rehearsal reports")
reports = latest_reports()
if not reports:
    st.info("No bridge routing write rehearsal reports found yet.")
else:
    choice = st.selectbox(
        "Rehearsal report",
        options=list(range(len(reports))),
        format_func=lambda i: f"{reports[i].name} — {reports[i].stat().st_mtime_ns}",
    )
    report_dir = reports[choice]
    json_path = report_dir / "phase19_bridge_routing_write_rehearsal.json"
    csv_path = report_dir / "phase19_bridge_routing_write_rehearsal.csv"
    md_path = report_dir / "phase19_bridge_routing_write_rehearsal.md"
    report = load_json(json_path)

    st.json(report.get("safety", {}))
    st.subheader("Blocker counts")
    st.json(report.get("counts", {}).get("blocker_counts", {}))

    rows = report.get("rehearsals", [])
    if rows:
        st.dataframe(rows, use_container_width=True, hide_index=True)
    else:
        st.info("No rehearsal rows were run, usually because there were no bridge apply preview rows.")

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
            "Download rehearsal CSV",
            csv_path.read_text(encoding="utf-8-sig"),
            "phase19_bridge_routing_write_rehearsal.csv",
            "text/csv",
        )

    st.download_button(
        "Download rehearsal JSON",
        json.dumps(report, indent=2, default=str),
        "phase19_bridge_routing_write_rehearsal.json",
        "application/json",
    )
