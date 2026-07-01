from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import requests
import streamlit as st


st.set_page_config(page_title="Bridge Routing HTTP Client Stub", page_icon="🧱", layout="wide")

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
            for p in BACKUP_DIR.glob("phase20_bridge_routing_http_client_stub_*")
            if p.is_dir() and (p / "phase20_bridge_routing_http_client_stub.json").exists()
        ],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )[:limit]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


st.title("🧱 Phase 20 Bridge Routing HTTP Client Stub")
st.caption("Stub preview only. No real bridge HTTP client, no bridge POST, and no execution endpoint.")

st.warning(
    "This page is HTTP-client-stub-only. It does not trigger bridge writes, does not write to the bridge, "
    "does not save platform records, does not call bridge POST endpoints, and does not call LACRM."
)

status_ok, status = get_json(f"{PLATFORM_API}/front-desk/routing/bridge-http-client-stub/status")
if not status_ok:
    st.error(f"Could not read bridge HTTP client stub status: {status}")
    st.stop()

c1, c2, c3, c4 = st.columns(4)
c1.metric("Safe default", status.get("safe_default", "unknown"))
c2.metric("Stub only", str(bool(status.get("bridge_routing_http_client_stub_only"))))
c3.metric("Real HTTP client", str(bool(status.get("real_bridge_http_client_implemented"))))
c4.metric("Bridge POST", "Not called" if not status.get("bridge_post_called") else "CHECK")

if (
    status.get("bridge_routing_http_client_stub_only")
    and not status.get("real_bridge_http_client_implemented")
    and not status.get("bridge_post_call_implemented")
    and not status.get("bridge_post_called")
):
    st.success("Safe stub confirmed: no real bridge HTTP client and no bridge POST.")
else:
    st.error("Review HTTP client stub safety flags before continuing.")

st.subheader("Stub status")
st.json(status)

st.subheader("How to generate stub preview")
st.code(
    "powershell -ExecutionPolicy Bypass -File scripts\\phase20_generate_bridge_routing_http_client_stub.ps1",
    language="powershell",
)

st.subheader("Generated stub reports")
reports = latest_reports()
if not reports:
    st.info("No bridge routing HTTP client stub report found yet.")
else:
    choice = st.selectbox(
        "HTTP client stub report",
        options=list(range(len(reports))),
        format_func=lambda i: f"{reports[i].name} - {reports[i].stat().st_mtime_ns}",
    )
    report_dir = reports[choice]
    json_path = report_dir / "phase20_bridge_routing_http_client_stub.json"
    artifacts_csv_path = report_dir / "phase20_bridge_routing_http_client_stub_artifacts.csv"
    blockers_csv_path = report_dir / "phase20_bridge_routing_http_client_stub_blockers.csv"
    report = load_json(json_path)

    st.json(report.get("safety", {}))
    st.subheader("Counts")
    st.json(report.get("counts", {}))

    preview = report.get("preview", {})
    st.subheader("Request template")
    st.json(preview.get("request_template", {}))

    blockers = preview.get("blockers", [])
    if blockers:
        st.subheader("Blockers")
        st.code("\n".join(str(x) for x in blockers), language="text")

    if artifacts_csv_path.exists():
        st.download_button(
            "Download release artifacts CSV",
            artifacts_csv_path.read_text(encoding="utf-8-sig"),
            "phase20_bridge_routing_http_client_stub_artifacts.csv",
            "text/csv",
        )

    if blockers_csv_path.exists():
        st.download_button(
            "Download blockers CSV",
            blockers_csv_path.read_text(encoding="utf-8-sig"),
            "phase20_bridge_routing_http_client_stub_blockers.csv",
            "text/csv",
        )

    st.download_button(
        "Download HTTP client stub JSON",
        json.dumps(report, indent=2, default=str),
        "phase20_bridge_routing_http_client_stub.json",
        "application/json",
    )
