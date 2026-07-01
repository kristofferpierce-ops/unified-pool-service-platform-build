from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import requests
import streamlit as st


st.set_page_config(page_title="Bridge Routing Write Dry-run Bundle", page_icon="📑", layout="wide")

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
            for p in BACKUP_DIR.glob("phase19_bridge_routing_write_dry_run_bundle_*")
            if p.is_dir() and (p / "phase19_bridge_routing_write_dry_run_bundle.json").exists()
        ],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )[:limit]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


st.title("📑 Phase 19 Bridge Routing Write Dry-run Bundle")
st.caption("Dry-run request bundle built from the Step 45 scaffold. No bridge HTTP client exists.")

st.warning(
    "This page is dry-run-bundle/status only. It does not trigger bridge writes, does not write to the bridge, "
    "does not save platform records, does not call bridge POST endpoints, and does not call LACRM."
)

status_ok, status = get_json(f"{PLATFORM_API}/front-desk/routing/bridge-write-dry-run-bundle/status")
if not status_ok:
    st.error(f"Could not read bridge write dry-run bundle status: {status}")
    st.stop()

c1, c2, c3, c4 = st.columns(4)
c1.metric("Safe default", status.get("safe_default", "unknown"))
c2.metric("Bundle only", str(bool(status.get("dry_run_bundle_only"))))
c3.metric("HTTP client", str(bool(status.get("bridge_http_client_implemented"))))
c4.metric("Bridge POST", "Not called" if not status.get("bridge_post_called") else "CHECK")

if (
    status.get("dry_run_bundle_only")
    and not status.get("bridge_http_client_implemented")
    and not status.get("bridge_post_call_implemented")
    and not status.get("bridge_post_called")
):
    st.success("Safe dry-run bundle confirmed: no bridge HTTP client and no bridge POST.")
else:
    st.error("Review dry-run bundle safety flags before continuing.")

st.subheader("Dry-run bundle status")
st.json(status)

st.subheader("How to generate dry-run bundle")
st.code(
    "powershell -ExecutionPolicy Bypass -File scripts\\phase19_generate_bridge_routing_write_dry_run_bundle.ps1",
    language="powershell",
)

st.subheader("Generated dry-run bundle reports")
reports = latest_reports()
if not reports:
    st.info("No bridge routing write dry-run bundle report found yet.")
else:
    choice = st.selectbox(
        "Dry-run bundle report",
        options=list(range(len(reports))),
        format_func=lambda i: f"{reports[i].name} - {reports[i].stat().st_mtime_ns}",
    )
    report_dir = reports[choice]
    json_path = report_dir / "phase19_bridge_routing_write_dry_run_bundle.json"
    rows_csv_path = report_dir / "phase19_bridge_routing_write_dry_run_bundle_rows.csv"
    blockers_csv_path = report_dir / "phase19_bridge_routing_write_dry_run_bundle_blockers.csv"
    report = load_json(json_path)

    st.json(report.get("safety", {}))
    st.subheader("Counts")
    st.json(report.get("counts", {}))

    rows = report.get("bundle", {}).get("bundle_rows", [])
    if rows:
        st.subheader("Bundle rows")
        st.dataframe(rows, use_container_width=True, hide_index=True)

    blockers = report.get("bundle", {}).get("blockers", [])
    if blockers:
        st.subheader("Blockers")
        st.code("\n".join(str(x) for x in blockers), language="text")

    if rows_csv_path.exists():
        st.download_button(
            "Download bundle rows CSV",
            rows_csv_path.read_text(encoding="utf-8-sig"),
            "phase19_bridge_routing_write_dry_run_bundle_rows.csv",
            "text/csv",
        )

    if blockers_csv_path.exists():
        st.download_button(
            "Download blockers CSV",
            blockers_csv_path.read_text(encoding="utf-8-sig"),
            "phase19_bridge_routing_write_dry_run_bundle_blockers.csv",
            "text/csv",
        )

    st.download_button(
        "Download dry-run bundle JSON",
        json.dumps(report, indent=2, default=str),
        "phase19_bridge_routing_write_dry_run_bundle.json",
        "application/json",
    )
