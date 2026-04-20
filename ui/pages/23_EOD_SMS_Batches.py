from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import requests
import streamlit as st


st.set_page_config(page_title="EOD SMS Batches", page_icon="🌙", layout="wide")

WORKSPACE = Path(os.getenv("KPS_WORKSPACE", r"C:\Users\krist\Desktop\unified_pool_service_platform_build"))
BACKUP_DIR = WORKSPACE / "backups"
BRIDGE_URL = os.getenv("BRIDGE_URL", "http://127.0.0.1:8000")
PLATFORM_API = os.getenv("PLATFORM_API_BASE_URL", "http://127.0.0.1:8010")


def get_json(url: str) -> tuple[bool, Any]:
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return True, response.json()
    except Exception as exc:  # pragma: no cover - runtime display
        return False, str(exc)


def get_text(url: str) -> tuple[bool, str]:
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return True, response.text
    except Exception as exc:  # pragma: no cover - runtime display
        return False, str(exc)


def latest_snapshots(limit: int = 20) -> list[Path]:
    if not BACKUP_DIR.exists():
        return []
    return sorted(
        BACKUP_DIR.glob("phase19_eod_sms_snapshot_*.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )[:limit]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def items_from_payload(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, list):
        return [item for item in value if isinstance(item, dict)]
    if isinstance(value, dict):
        for key in ("items", "batches", "results", "queue", "sms_batches"):
            if isinstance(value.get(key), list):
                return [item for item in value[key] if isinstance(item, dict)]
    return []


def rows_from_batches(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in items[:250]:
        rows.append(
            {
                "id": item.get("id"),
                "date": item.get("batch_date"),
                "phone": item.get("external_phone"),
                "latest": item.get("latest_message_at"),
                "status": item.get("status"),
                "has_summary": bool(item.get("summary")),
                "has_next_steps": bool(item.get("next_steps")),
                "auto_attached": item.get("auto_attached"),
            }
        )
    return rows


st.title("🌙 Phase 19 EOD SMS Batches")
st.caption("Read-only view of the original bridge end-of-day SMS batch workflow.")

st.warning(
    "This page is read-only. It does not press the bridge Run EOD button, "
    "does not force rebuild batches, does not call LACRM, and does not modify bridge state."
)

bridge_ok, bridge_html = get_text(BRIDGE_URL)
bridge_health_ok, bridge_health = get_json(f"{BRIDGE_URL}/health")
active_ok, active_payload = get_json(f"{BRIDGE_URL}/api/sms/batches?view=active")
processed_ok, processed_payload = get_json(f"{BRIDGE_URL}/api/sms/batches?view=processed")
platform_ok, platform_health = get_json(f"{PLATFORM_API}/health")
safety_ok, safety = get_json(f"{PLATFORM_API}/front-desk/lacrm-apply/status")
text_quality_ok, text_quality = get_json(f"{PLATFORM_API}/front-desk/text-quality/summary?sample_limit=5")

markers = {
    "data_hub_title": bridge_ok and "Keys Pool Service Data Hub" in bridge_html,
    "run_eod_button": bridge_ok and "runEodBtn" in bridge_html,
    "text_summaries_tab": bridge_ok and "Text summaries" in bridge_html,
    "force_batch_button": bridge_ok and "forceBatchBtn" in bridge_html,
    "sms_summary_text": bridge_ok and "smsSummaryText" in bridge_html,
}

active_items = items_from_payload(active_payload) if active_ok else []
processed_items = items_from_payload(processed_payload) if processed_ok else []
live_enabled = bool(safety.get("live_write_enabled")) if isinstance(safety, dict) else False
live_armed = bool(safety.get("live_write_armed")) if isinstance(safety, dict) else False

c1, c2, c3, c4 = st.columns(4)
c1.metric("Bridge 8000", "OK" if bridge_health_ok else "Check")
c2.metric("Run EOD marker", "Present" if markers["run_eod_button"] else "Check")
c3.metric("Active batches", len(active_items))
c4.metric("Live LACRM writes", "OFF" if not live_enabled and not live_armed else "CHECK")

st.subheader("Bridge EOD/Text Summary UI markers")
st.json(markers)

tab_active, tab_processed, tab_snapshots = st.tabs(["Active bridge batches", "Processed bridge batches", "Snapshots"])

with tab_active:
    if active_ok:
        rows = rows_from_batches(active_items)
        if rows:
            st.dataframe(rows, use_container_width=True, hide_index=True)
        else:
            st.info("Bridge active SMS endpoint responded, but no active batches were returned.")
    else:
        st.warning(f"Could not read active bridge SMS batches: {active_payload}")

with tab_processed:
    if processed_ok:
        rows = rows_from_batches(processed_items)
        if rows:
            st.dataframe(rows, use_container_width=True, hide_index=True)
        else:
            st.info("Bridge processed SMS endpoint responded, but no processed batches were returned.")
    else:
        st.warning(f"Could not read processed bridge SMS batches: {processed_payload}")

with tab_snapshots:
    snapshots = latest_snapshots()
    if not snapshots:
        st.info("No EOD SMS snapshots found yet. Run `scripts\\phase19_generate_eod_sms_snapshot.ps1`.")
    else:
        choice = st.selectbox(
            "Snapshot",
            options=list(range(len(snapshots))),
            format_func=lambda i: f"{snapshots[i].name} — {snapshots[i].stat().st_mtime_ns}",
        )
        snapshot = load_json(snapshots[choice])
        st.json(snapshot)
        st.download_button(
            "Download EOD SMS snapshot JSON",
            json.dumps(snapshot, indent=2, default=str),
            "phase19_eod_sms_snapshot.json",
            "application/json",
        )

st.subheader("Platform context")
st.json(
    {
        "platform_health_ok": platform_ok,
        "text_quality_ok": text_quality_ok,
        "text_quality_summary": text_quality if isinstance(text_quality, dict) else {},
        "lacrm_safety_endpoint_ok": safety_ok,
        "live_write_enabled": live_enabled,
        "live_write_armed": live_armed,
        "read_only_only": True,
    }
)

st.subheader("Original bridge")
st.markdown(f"[Open original KPS Bridge / Data Hub UI]({BRIDGE_URL})")
