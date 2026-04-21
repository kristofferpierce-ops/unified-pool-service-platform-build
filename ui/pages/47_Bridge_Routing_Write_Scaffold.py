from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import requests
import streamlit as st


st.set_page_config(page_title="Bridge Routing Write Scaffold", page_icon="🧱", layout="wide")

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
        [
            p
            for p in BACKUP_DIR.glob("phase19_bridge_routing_write_scaffold_*")
            if p.is_dir() and (p / "phase19_bridge_routing_write_scaffold.json").exists()
        ],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )[:limit]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


st.title("🧱 Phase 19 Bridge Routing Write Scaffold")
st.caption("Disabled-by-default scaffold preview. No bridge HTTP client or POST implementation exists in Step 45.")

st.warning(
    "This page is scaffold/status only. It does not trigger bridge writes, does not write to the bridge, "
    "does not save platform records, does not call bridge POST endpoints, and does not call LACRM."
)

status_ok, status = get_json(f"{PLATFORM_API}/front-desk/routing/bridge-write-executor/status")
if not status_ok:
    st.error(f"Could not read bridge write scaffold status: {status}")
    st.stop()

c1, c2, c3, c4 = st.columns(4)
c1.metric("Safe default", status.get("safe_default", "unknown"))
c2.metric("Write enabled", str(bool(status.get("bridge_routing_write_enabled"))))
c3.metric("Write armed", str(bool(status.get("bridge_routing_write_armed"))))
c4.metric("Bridge POST implemented", str(bool(status.get("bridge_post_call_implemented"))))

if (
    not status.get("bridge_post_call_implemented")
    and not status.get("bridge_post_called")
    and not status.get("execution_endpoint_available")
):
    st.success("Safe scaffold confirmed: no bridge POST implementation and no execution endpoint.")
else:
    st.error("Review scaffold safety flags before continuing.")

st.subheader("Scaffold gate status")
st.json(status)

st.subheader("How to run safe scaffold preview")
st.code(
    "powershell -ExecutionPolicy Bypass -File scripts\\phase19_run_bridge_routing_write_scaffold.ps1",
    language="powershell",
)

st.subheader("Generated scaffold reports")
reports = latest_reports()
if not reports:
    st.info("No bridge routing write scaffold report found yet.")
else:
    choice = st.selectbox(
        "Scaffold report",
        options=list(range(len(reports))),
        format_func=lambda i: f"{reports[i].name} - {reports[i].stat().st_mtime_ns}",
    )
    report_dir = reports[choice]
    json_path = report_dir / "phase19_bridge_routing_write_scaffold.json"
    blockers_csv_path = report_dir / "phase19_bridge_routing_write_scaffold_blockers.csv"
    plan_items_csv_path = report_dir / "phase19_bridge_routing_write_scaffold_plan_items.csv"
    report = load_json(json_path)

    st.json(report.get("safety", {}))
    st.subheader("Counts")
    st.json(report.get("counts", {}))

    blockers = report.get("preview", {}).get("blockers", [])
    if blockers:
        st.subheader("Blockers")
        st.code("\n".join(str(x) for x in blockers), language="text")

    envelope = report.get("preview", {}).get("request_envelope_preview", {})
    st.subheader("Request envelope preview")
    st.json(envelope)

    if blockers_csv_path.exists():
        st.download_button(
            "Download blockers CSV",
            blockers_csv_path.read_text(encoding="utf-8-sig"),
            "phase19_bridge_routing_write_scaffold_blockers.csv",
            "text/csv",
        )

    if plan_items_csv_path.exists():
        st.download_button(
            "Download plan items CSV",
            plan_items_csv_path.read_text(encoding="utf-8-sig"),
            "phase19_bridge_routing_write_scaffold_plan_items.csv",
            "text/csv",
        )

    st.download_button(
        "Download scaffold JSON",
        json.dumps(report, indent=2, default=str),
        "phase19_bridge_routing_write_scaffold.json",
        "application/json",
    )
