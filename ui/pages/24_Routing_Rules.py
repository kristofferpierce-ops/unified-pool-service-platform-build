from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import requests
import streamlit as st


st.set_page_config(page_title="Routing Rules", page_icon="🧭", layout="wide")

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
        BACKUP_DIR.glob("phase19_routing_rules_snapshot_*.json"),
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


def routing_rows(items: list[dict[str, Any]], source_view: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in items[:500]:
        rule = item.get("routing_rule") if isinstance(item, dict) else None
        if isinstance(rule, dict):
            rows.append(
                {
                    "source": source_view,
                    "phone": rule.get("phone") or item.get("external_phone"),
                    "mode": rule.get("mode"),
                    "owner_type": rule.get("owner_type"),
                    "label": rule.get("label"),
                    "default_contact_count": len(rule.get("default_contact_ids") or []),
                    "batch_status": item.get("status"),
                    "batch_date": item.get("batch_date"),
                    "updated_at": rule.get("updated_at"),
                }
            )
        else:
            rows.append(
                {
                    "source": source_view,
                    "phone": item.get("external_phone"),
                    "mode": "",
                    "owner_type": "",
                    "label": "",
                    "default_contact_count": 0,
                    "batch_status": item.get("status"),
                    "batch_date": item.get("batch_date"),
                    "updated_at": "",
                }
            )
    return rows


st.title("🧭 Phase 19 Routing Rules")
st.caption("Read-only bridge routing-rule parity viewer.")

st.warning(
    "This page is read-only. It does not save routing rules, does not call bridge POST endpoints, "
    "does not call LACRM, and does not modify bridge state."
)

bridge_ok, bridge_html = get_text(BRIDGE_URL)
bridge_health_ok, bridge_health = get_json(f"{BRIDGE_URL}/health")
active_ok, active_payload = get_json(f"{BRIDGE_URL}/api/sms/batches?view=active")
processed_ok, processed_payload = get_json(f"{BRIDGE_URL}/api/sms/batches?view=processed")
routing_endpoint_ok, routing_endpoint_payload = get_json(f"{BRIDGE_URL}/api/routing-rules")
safety_ok, safety = get_json(f"{PLATFORM_API}/front-desk/lacrm-apply/status")

markers = {
    "data_hub_title": bridge_ok and "Keys Pool Service Data Hub" in bridge_html,
    "routing_rule_summary": bridge_ok and "routingRuleSummary" in bridge_html,
    "set_manual_button": bridge_ok and "setManualBtn" in bridge_html,
    "text_summaries_tab": bridge_ok and "Text summaries" in bridge_html,
}

active_items = items_from_payload(active_payload) if active_ok else []
processed_items = items_from_payload(processed_payload) if processed_ok else []
rows = routing_rows(active_items, "active") + routing_rows(processed_items, "processed")

live_enabled = bool(safety.get("live_write_enabled")) if isinstance(safety, dict) else False
live_armed = bool(safety.get("live_write_armed")) if isinstance(safety, dict) else False

c1, c2, c3, c4 = st.columns(4)
c1.metric("Bridge 8000", "OK" if bridge_health_ok else "Check")
c2.metric("Routing UI marker", "Present" if markers["routing_rule_summary"] else "Check")
c3.metric("Rule rows", len(rows))
c4.metric("Live LACRM writes", "OFF" if not live_enabled and not live_armed else "CHECK")

st.subheader("Bridge routing UI markers")
st.json(markers)

st.subheader("Routing rows from bridge SMS batches")
if rows:
    mode_filter = st.multiselect(
        "Mode filter",
        sorted({str(row.get("mode") or "blank") for row in rows}),
        default=sorted({str(row.get("mode") or "blank") for row in rows}),
    )
    filtered = [row for row in rows if str(row.get("mode") or "blank") in mode_filter]
    st.dataframe(filtered, use_container_width=True, hide_index=True)
else:
    st.info("No routing rows were derived from bridge SMS batches.")

with st.expander("Bridge /api/routing-rules endpoint status"):
    st.json({"ok": routing_endpoint_ok, "payload": routing_endpoint_payload if routing_endpoint_ok else str(routing_endpoint_payload)})

st.subheader("Safety")
st.json(
    {
        "lacrm_safety_endpoint_ok": safety_ok,
        "live_write_enabled": live_enabled,
        "live_write_armed": live_armed,
        "read_only_only": True,
    }
)

st.subheader("Generated routing snapshots")
snapshots = latest_snapshots()
if not snapshots:
    st.info("No routing snapshots found yet. Run `scripts\\phase19_generate_routing_rules_snapshot.ps1`.")
else:
    choice = st.selectbox(
        "Snapshot",
        options=list(range(len(snapshots))),
        format_func=lambda i: f"{snapshots[i].name} — {snapshots[i].stat().st_mtime_ns}",
    )
    snapshot = load_json(snapshots[choice])
    st.json(snapshot)
    st.download_button(
        "Download routing-rules snapshot JSON",
        json.dumps(snapshot, indent=2, default=str),
        "phase19_routing_rules_snapshot.json",
        "application/json",
    )

st.subheader("Original bridge")
st.markdown(f"[Open original KPS Bridge / Data Hub UI]({BRIDGE_URL})")
