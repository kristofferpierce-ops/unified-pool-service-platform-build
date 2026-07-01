from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import requests
import streamlit as st


st.set_page_config(page_title="Call Context", page_icon="â˜Žï¸", layout="wide")

WORKSPACE = Path(os.getenv("KPS_WORKSPACE", r"C:\Users\krist\Desktop\unified_pool_service_platform_build"))
BACKUP_DIR = WORKSPACE / "backups"
BRIDGE_URL = os.getenv("BRIDGE_URL", "http://127.0.0.1:8000")
PLATFORM_API = os.getenv("PLATFORM_API_BASE_URL", "http://127.0.0.1:8010")


def get_json(url: str) -> tuple[bool, Any]:
    try:
        response = requests.get(url, timeout=8)
        response.raise_for_status()
        return True, response.json()
    except Exception as exc:  # pragma: no cover - runtime display
        return False, str(exc)


def get_text(url: str) -> tuple[bool, str]:
    try:
        response = requests.get(url, timeout=8)
        response.raise_for_status()
        return True, response.text
    except Exception as exc:  # pragma: no cover - runtime display
        return False, str(exc)


def latest_snapshots(limit: int = 20) -> list[Path]:
    if not BACKUP_DIR.exists():
        return []
    return sorted(
        BACKUP_DIR.glob("phase19_call_context_snapshot_*.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )[:limit]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def count_items(value: Any) -> int:
    if isinstance(value, list):
        return len(value)
    if isinstance(value, dict):
        for key in ("items", "calls", "queue", "results"):
            if isinstance(value.get(key), list):
                return len(value[key])
    return 0


def preview_rows(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, list):
        items = value
    elif isinstance(value, dict):
        items = []
        for key in ("items", "calls", "queue", "results"):
            maybe_items = value.get(key)
            if isinstance(maybe_items, list):
                items = maybe_items
                break
    else:
        items = []

    rows: list[dict[str, Any]] = []
    for item in items[:25]:
        if not isinstance(item, dict):
            continue

        summary = item.get("summary") or item.get("subject") or item.get("transcript") or ""

        rows.append(
            {
                "id": item.get("id") or item.get("call_id") or item.get("session_id"),
                "phone": item.get("external_phone") or item.get("from_phone") or item.get("phone"),
                "status": item.get("status") or item.get("call_status") or item.get("direction"),
                "latest": item.get("latest_message_at") or item.get("created_at") or item.get("start_time"),
                "summary": str(summary)[:120],
            }
        )
    return rows


st.title("â˜Žï¸ Phase 19 Call Context")
st.caption("Read-only bridge incoming-call/HUD context viewer.")

st.warning(
    "This page is read-only. It does not create CRM notes, does not create tasks, "
    "does not call LACRM, and does not modify bridge state."
)

bridge_ok, bridge_html = get_text(BRIDGE_URL)
bridge_health_ok, bridge_health = get_json(f"{BRIDGE_URL}/health")
active_ok, active_calls = get_json(f"{BRIDGE_URL}/api/calls?view=active")
processed_ok, processed_calls = get_json(f"{BRIDGE_URL}/api/calls?view=processed")
platform_ok, platform_health = get_json(f"{PLATFORM_API}/health")
safety_ok, safety = get_json(f"{PLATFORM_API}/front-desk/lacrm-apply/status")

markers = {
    "data_hub_title": bridge_ok and "Keys Pool Service Data Hub" in bridge_html,
    "incoming_hud": bridge_ok and "incomingHud" in bridge_html,
    "hud_history_list": bridge_ok and "hudHistoryList" in bridge_html,
    "calls_tab": bridge_ok and "Calls + voicemail" in bridge_html,
    "manual_search": bridge_ok and "callSearchInput" in bridge_html,
}

live_enabled = bool(safety.get("live_write_enabled")) if isinstance(safety, dict) else False
live_armed = bool(safety.get("live_write_armed")) if isinstance(safety, dict) else False

c1, c2, c3, c4 = st.columns(4)
c1.metric("Bridge 8000", "OK" if bridge_health_ok else "Check")
c2.metric("HUD marker", "Present" if markers["incoming_hud"] else "Check")
c3.metric("Active calls", count_items(active_calls) if active_ok else "n/a")
c4.metric("Live LACRM writes", "OFF" if not live_enabled and not live_armed else "CHECK")

st.subheader("Bridge HUD markers")
st.json(markers)

if active_ok:
    st.subheader("Active bridge calls / voicemail queue")
    rows = preview_rows(active_calls)
    if rows:
        st.dataframe(rows, use_container_width=True, hide_index=True)
    else:
        st.info("Bridge active call endpoint responded, but no active call rows were returned.")
else:
    st.warning(f"Could not read active calls from bridge: {active_calls}")

with st.expander("Processed bridge calls preview"):
    if processed_ok:
        rows = preview_rows(processed_calls)
        if rows:
            st.dataframe(rows, use_container_width=True, hide_index=True)
        else:
            st.info("Processed endpoint responded, but no rows were returned.")
    else:
        st.warning(str(processed_calls))

st.subheader("Safety")
st.json(
    {
        "platform_health_ok": platform_ok,
        "lacrm_safety_endpoint_ok": safety_ok,
        "live_write_enabled": live_enabled,
        "live_write_armed": live_armed,
        "read_only_only": True,
    }
)

st.subheader("Generated call-context snapshots")
snapshots = latest_snapshots()
if not snapshots:
    st.info("No call-context snapshots found yet. Run `scripts\\phase19_generate_call_context_snapshot.ps1`.")
else:
    choice = st.selectbox(
        "Snapshot",
        options=list(range(len(snapshots))),
        format_func=lambda i: f"{snapshots[i].name} â€” {snapshots[i].stat().st_mtime_ns}",
    )
    snapshot = load_json(snapshots[choice])
    st.json(snapshot)
    st.download_button(
        "Download call-context snapshot JSON",
        json.dumps(snapshot, indent=2, default=str),
        "phase19_call_context_snapshot.json",
        "application/json",
    )

st.subheader("Original bridge")
st.markdown(f"[Open original KPS Bridge / Data Hub UI]({BRIDGE_URL})")

