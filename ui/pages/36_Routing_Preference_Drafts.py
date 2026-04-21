from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import requests
import streamlit as st


st.set_page_config(page_title="Routing Preference Drafts", page_icon="🧱", layout="wide")

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


def latest_checks(limit: int = 20) -> list[Path]:
    if not BACKUP_DIR.exists():
        return []
    return sorted(
        [p for p in BACKUP_DIR.glob("phase19_routing_preference_draft_check_*") if p.is_dir()],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )[:limit]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


st.title("🧱 Phase 19 Routing Preference Drafts")
st.caption("Read-only draft schema foundation for approved routing preferences.")

st.warning(
    "This page is read-only. Step 34 does not create drafts, does not save routing rules, "
    "does not call bridge POST endpoints, and does not call LACRM."
)

status_ok, status = get_json(f"{PLATFORM_API}/front-desk/routing/preference-drafts/status")
drafts_ok, drafts_payload = get_json(f"{PLATFORM_API}/front-desk/routing/preference-drafts?limit=250")

if not status_ok:
    st.error(f"Could not read routing preference draft status: {status}")
    st.stop()

c1, c2, c3, c4 = st.columns(4)
c1.metric("Schema", status.get("schema_version", "unknown"))
c2.metric("Total drafts", status.get("total_drafts", 0))
c3.metric("Draft creation", "OFF" if not status.get("draft_creation_enabled") else "CHECK")
c4.metric("Bridge writes", "OFF" if not status.get("bridge_post_enabled") else "CHECK")

if status.get("read_only") and not status.get("draft_creation_enabled") and not status.get("draft_write_endpoint_implemented"):
    st.success("Safe draft schema confirmed: read-only API, no draft creation, no bridge write path.")
else:
    st.error("Review draft safety flags before continuing.")

st.subheader("Draft status")
st.json(status)

st.subheader("Draft list")
if drafts_ok:
    rows = drafts_payload.get("drafts", []) if isinstance(drafts_payload, dict) else []
    if rows:
        st.dataframe(rows, use_container_width=True, hide_index=True)
    else:
        st.info("No routing preference drafts exist yet. This is expected in Step 34 because draft creation is not implemented.")
else:
    st.warning(f"Could not read routing preference drafts: {drafts_payload}")

st.subheader("Generated draft checks")
checks = latest_checks()
if not checks:
    st.info("No draft check reports found yet. Run `scripts\\phase19_check_routing_preference_drafts.ps1`.")
else:
    choice = st.selectbox(
        "Draft check report",
        options=list(range(len(checks))),
        format_func=lambda i: f"{checks[i].name} — {checks[i].stat().st_mtime_ns}",
    )
    check_dir = checks[choice]
    report_path = check_dir / "phase19_routing_preference_draft_check.json"
    st.json(load_json(report_path))

st.download_button(
    "Download draft status JSON",
    json.dumps(status, indent=2, default=str),
    "phase19_routing_preference_draft_status.json",
    "application/json",
)

if drafts_ok:
    st.download_button(
        "Download routing preference drafts JSON",
        json.dumps(drafts_payload, indent=2, default=str),
        "phase19_routing_preference_drafts.json",
        "application/json",
    )
