from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import requests
import streamlit as st


st.set_page_config(page_title="Bridge Routing Network Transport Guard", page_icon="🛡️", layout="wide")

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
            for p in BACKUP_DIR.glob("phase20_bridge_routing_network_transport_guard_*")
            if p.is_dir() and (p / "phase20_bridge_routing_network_transport_guard.json").exists()
        ],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )[:limit]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


st.title("🛡️ Phase 20 Bridge Routing Network Transport Guard")
st.caption("Design guard only. No real network transport, no bridge HTTP client, and no bridge POST.")

st.warning(
    "This page is network-transport-guard-only. It does not trigger bridge writes, does not write to the bridge, "
    "does not save platform records, does not call bridge POST endpoints, and does not call LACRM."
)

status_ok, status = get_json(f"{PLATFORM_API}/front-desk/routing/bridge-network-transport-guard/status")
if not status_ok:
    st.error(f"Could not read bridge network transport guard status: {status}")
    st.stop()

c1, c2, c3, c4 = st.columns(4)
c1.metric("Safe default", status.get("safe_default", "unknown"))
c2.metric("Guard only", str(bool(status.get("bridge_routing_network_transport_guard_only"))))
c3.metric("Network transport", str(bool(status.get("network_transport_implemented"))))
c4.metric("Bridge POST", "Not called" if not status.get("bridge_post_called") else "CHECK")

if (
    status.get("bridge_routing_network_transport_guard_only")
    and not status.get("real_bridge_http_client_implemented")
    and not status.get("network_transport_implemented")
    and not status.get("bridge_post_call_implemented")
    and not status.get("bridge_post_called")
):
    st.success("Safe guard confirmed: no real HTTP client, no network transport, and no bridge POST.")
else:
    st.error("Review network transport guard safety flags before continuing.")

st.subheader("Network transport guard status")
st.json(status)

st.subheader("How to generate guard preview")
st.code(
    "powershell -ExecutionPolicy Bypass -File scripts\\phase20_generate_bridge_routing_network_transport_guard.ps1",
    language="powershell",
)

st.subheader("Generated guard reports")
reports = latest_reports()
if not reports:
    st.info("No bridge routing network transport guard report found yet.")
else:
    choice = st.selectbox(
        "Network transport guard report",
        options=list(range(len(reports))),
        format_func=lambda i: f"{reports[i].name} - {reports[i].stat().st_mtime_ns}",
    )
    report_dir = reports[choice]
    json_path = report_dir / "phase20_bridge_routing_network_transport_guard.json"
    artifacts_csv_path = report_dir / "phase20_bridge_routing_network_transport_guard_artifacts.csv"
    blockers_csv_path = report_dir / "phase20_bridge_routing_network_transport_guard_blockers.csv"
    report = load_json(json_path)

    st.json(report.get("safety", {}))
    st.subheader("Counts")
    st.json(report.get("counts", {}))

    preview = report.get("preview", {})
    st.subheader("Transport design contract")
    st.json(preview.get("transport_design_contract", {}))

    blockers = preview.get("blockers", [])
    if blockers:
        st.subheader("Blockers")
        st.code("\n".join(str(x) for x in blockers), language="text")

    if artifacts_csv_path.exists():
        st.download_button(
            "Download release artifacts CSV",
            artifacts_csv_path.read_text(encoding="utf-8-sig"),
            "phase20_bridge_routing_network_transport_guard_artifacts.csv",
            "text/csv",
        )

    if blockers_csv_path.exists():
        st.download_button(
            "Download blockers CSV",
            blockers_csv_path.read_text(encoding="utf-8-sig"),
            "phase20_bridge_routing_network_transport_guard_blockers.csv",
            "text/csv",
        )

    st.download_button(
        "Download network transport guard JSON",
        json.dumps(report, indent=2, default=str),
        "phase20_bridge_routing_network_transport_guard.json",
        "application/json",
    )
