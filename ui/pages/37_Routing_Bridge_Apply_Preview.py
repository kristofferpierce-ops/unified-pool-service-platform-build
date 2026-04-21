from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import requests
import streamlit as st


st.set_page_config(page_title="Routing Bridge Apply Preview", page_icon="🧪", layout="wide")

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
        [p for p in BACKUP_DIR.glob("phase19_routing_bridge_apply_preview_*") if p.is_dir()],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )[:limit]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


st.title("🧪 Phase 19 Routing Bridge Apply Preview")
st.caption("Dry-run preview of bridge routing payloads from platform routing preference drafts.")

st.warning(
    "This page is preview-only. It does not write to the bridge, does not save platform records, "
    "does not call bridge POST endpoints, and does not call LACRM."
)

status_ok, status = get_json(f"{PLATFORM_API}/front-desk/routing/bridge-apply-preview/status")
preview_ok, preview = get_json(f"{PLATFORM_API}/front-desk/routing/bridge-apply-preview?limit=500&include_blocked=true")

if not status_ok:
    st.error(f"Could not read bridge apply preview status: {status}")
    st.stop()

c1, c2, c3, c4 = st.columns(4)
c1.metric("Total drafts", status.get("total_drafts", 0))
c2.metric("Previewable drafts", status.get("previewable_drafts", 0))
c3.metric("Bridge apply", "OFF" if not status.get("bridge_apply_enabled") else "CHECK")
c4.metric("Bridge POST", "Not called" if not status.get("bridge_post_called") else "CHECK")

if status.get("read_only") and status.get("preview_only") and not status.get("bridge_apply_enabled") and not status.get("bridge_post_called"):
    st.success("Safe preview confirmed: no bridge write, no platform write, no LACRM call.")
else:
    st.error("Review bridge apply preview safety flags before continuing.")

st.subheader("Preview status")
st.json(status)

st.subheader("Preview rows")
if preview_ok:
    rows = preview.get("preview_rows", []) if isinstance(preview, dict) else []
    if rows:
        preview_values = sorted({str(row.get("previewable")) for row in rows})
        selected = st.multiselect("Previewable filter", preview_values, default=preview_values)
        filtered = [row for row in rows if str(row.get("previewable")) in selected]
        st.dataframe(filtered, use_container_width=True, hide_index=True)
    else:
        st.info("No routing preference drafts exist yet. This is expected until a later draft-creation step.")
else:
    st.warning(f"Could not read preview rows: {preview}")

st.subheader("Generated preview reports")
reports = latest_reports()
if not reports:
    st.info("No bridge apply preview reports found yet. Run `scripts\\phase19_generate_routing_bridge_apply_preview.ps1`.")
else:
    choice = st.selectbox(
        "Preview report",
        options=list(range(len(reports))),
        format_func=lambda i: f"{reports[i].name} — {reports[i].stat().st_mtime_ns}",
    )
    report_dir = reports[choice]
    report_path = report_dir / "phase19_routing_bridge_apply_preview.json"
    st.json(load_json(report_path))

st.download_button(
    "Download bridge apply preview status JSON",
    json.dumps(status, indent=2, default=str),
    "phase19_routing_bridge_apply_preview_status.json",
    "application/json",
)

if preview_ok:
    st.download_button(
        "Download bridge apply preview JSON",
        json.dumps(preview, indent=2, default=str),
        "phase19_routing_bridge_apply_preview.json",
        "application/json",
    )
