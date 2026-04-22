from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import requests
import streamlit as st


st.set_page_config(page_title="Bridge Routing Network Transport Interface Scaffold", page_icon="🧱", layout="wide")

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
            for p in BACKUP_DIR.glob("phase20_bridge_routing_network_transport_interface_scaffold_*")
            if p.is_dir() and (p / "phase20_bridge_routing_network_transport_interface_scaffold.json").exists()
        ],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )[:limit]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


st.title("🧱 Phase 20 Bridge Routing Network Transport Interface Scaffold")
st.caption("Interface scaffold only. No real network transport, no socket, no bridge HTTP client, and no bridge POST.")

st.warning(
    "This page is network-transport-interface-scaffold-only. It does not trigger bridge writes, does not write to the bridge, "
    "does not save platform records, does not call bridge POST endpoints, and does not call LACRM."
)

status_ok, status = get_json(f"{PLATFORM_API}/front-desk/routing/bridge-network-transport-interface-scaffold/status")
if not status_ok:
    st.error(f"Could not read bridge network transport interface scaffold status: {status}")
    st.stop()

c1, c2, c3, c4 = st.columns(4)
c1.metric("Safe default", status.get("safe_default", "unknown"))
c2.metric("Scaffold only", str(bool(status.get("bridge_routing_network_transport_interface_scaffold_only"))))
c3.metric("Socket opened", str(bool(status.get("network_socket_opened"))))
c4.metric("Bridge POST", "Not called" if not status.get("bridge_post_called") else "CHECK")

if (
    status.get("bridge_routing_network_transport_interface_scaffold_only")
    and not status.get("real_bridge_http_client_implemented")
    and not status.get("network_transport_implemented")
    and not status.get("network_socket_opened")
    and not status.get("bridge_post_call_implemented")
    and not status.get("bridge_post_called")
):
    st.success("Safe interface scaffold confirmed: no socket, no real transport, and no bridge POST.")
else:
    st.error("Review network transport interface scaffold safety flags before continuing.")

st.subheader("Interface scaffold status")
st.json(status)

st.subheader("How to generate interface scaffold preview")
st.code(
    "powershell -ExecutionPolicy Bypass -File scripts\\phase20_generate_bridge_routing_network_transport_interface_scaffold.ps1",
    language="powershell",
)

st.subheader("Generated interface scaffold reports")
reports = latest_reports()
if not reports:
    st.info("No bridge routing network transport interface scaffold report found yet.")
else:
    choice = st.selectbox(
        "Network transport interface scaffold report",
        options=list(range(len(reports))),
        format_func=lambda i: f"{reports[i].name} - {reports[i].stat().st_mtime_ns}",
    )
    report_dir = reports[choice]
    json_path = report_dir / "phase20_bridge_routing_network_transport_interface_scaffold.json"
    classes_csv_path = report_dir / "phase20_bridge_routing_network_transport_interface_scaffold_classes.csv"
    blockers_csv_path = report_dir / "phase20_bridge_routing_network_transport_interface_scaffold_blockers.csv"
    report = load_json(json_path)

    st.json(report.get("safety", {}))
    st.subheader("Counts")
    st.json(report.get("counts", {}))

    preview = report.get("preview", {})
    st.subheader("Interface scaffold")
    st.json(preview.get("interface_scaffold", {}))

    st.subheader("Sample request")
    st.json(preview.get("sample_request", {}))

    st.subheader("Sample result")
    st.json(preview.get("sample_result", {}))

    blockers = preview.get("blockers", [])
    if blockers:
        st.subheader("Blockers")
        st.code("\n".join(str(x) for x in blockers), language="text")

    if classes_csv_path.exists():
        st.download_button(
            "Download scaffold classes CSV",
            classes_csv_path.read_text(encoding="utf-8-sig"),
            "phase20_bridge_routing_network_transport_interface_scaffold_classes.csv",
            "text/csv",
        )

    if blockers_csv_path.exists():
        st.download_button(
            "Download blockers CSV",
            blockers_csv_path.read_text(encoding="utf-8-sig"),
            "phase20_bridge_routing_network_transport_interface_scaffold_blockers.csv",
            "text/csv",
        )

    st.download_button(
        "Download network transport interface scaffold JSON",
        json.dumps(report, indent=2, default=str),
        "phase20_bridge_routing_network_transport_interface_scaffold.json",
        "application/json",
    )
