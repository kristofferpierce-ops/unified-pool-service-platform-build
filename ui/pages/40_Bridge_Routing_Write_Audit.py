from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import requests
import streamlit as st


st.set_page_config(page_title="Bridge Routing Write Audit", page_icon="🧾", layout="wide")

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
        [p for p in BACKUP_DIR.glob("phase19_bridge_routing_write_audit_check_*") if p.is_dir()],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )[:limit]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


st.title("🧾 Phase 19 Bridge Routing Write Audit")
st.caption("Read-only audit/rollback ledger foundation for future bridge routing writes.")

st.warning(
    "This page is read-only. Step 38 does not create audit rows, does not write to the bridge, "
    "does not save platform records through this page, does not call bridge POST endpoints, and does not call LACRM."
)

status_ok, status = get_json(f"{PLATFORM_API}/front-desk/routing/bridge-write-audit/status")
audits_ok, audits_payload = get_json(f"{PLATFORM_API}/front-desk/routing/bridge-write-audit?limit=250")

if not status_ok:
    st.error(f"Could not read bridge write audit status: {status}")
    st.stop()

c1, c2, c3, c4 = st.columns(4)
c1.metric("Schema", status.get("schema_version", "unknown"))
c2.metric("Audit rows", status.get("total_audit_rows", 0))
c3.metric("Audit writes", "OFF" if not status.get("audit_write_enabled") else "CHECK")
c4.metric("Bridge POST rows", status.get("bridge_post_called_rows", 0))

if (
    status.get("read_only")
    and not status.get("audit_write_endpoint_implemented")
    and not status.get("rollback_write_endpoint_implemented")
    and not status.get("bridge_post_enabled")
):
    st.success("Safe audit foundation confirmed: read-only API, no audit writer, no rollback writer, no bridge write.")
else:
    st.error("Review bridge write audit safety flags before continuing.")

st.subheader("Audit status")
st.json(status)

st.subheader("Audit rows")
if audits_ok:
    rows = audits_payload.get("audit_rows", []) if isinstance(audits_payload, dict) else []
    if rows:
        st.dataframe(rows, use_container_width=True, hide_index=True)
    else:
        st.info("No bridge routing write audit rows exist yet. This is expected in Step 38 because audit writes are not implemented.")
else:
    st.warning(f"Could not read audit rows: {audits_payload}")

st.subheader("Generated audit checks")
checks = latest_checks()
if not checks:
    st.info("No bridge write audit check reports found yet. Run `scripts\\phase19_check_bridge_routing_write_audit.ps1`.")
else:
    choice = st.selectbox(
        "Audit check report",
        options=list(range(len(checks))),
        format_func=lambda i: f"{checks[i].name} — {checks[i].stat().st_mtime_ns}",
    )
    check_dir = checks[choice]
    report_path = check_dir / "phase19_bridge_routing_write_audit_check.json"
    st.json(load_json(report_path))

st.download_button(
    "Download bridge write audit status JSON",
    json.dumps(status, indent=2, default=str),
    "phase19_bridge_routing_write_audit_status.json",
    "application/json",
)

if audits_ok:
    st.download_button(
        "Download bridge write audit rows JSON",
        json.dumps(audits_payload, indent=2, default=str),
        "phase19_bridge_routing_write_audit_rows.json",
        "application/json",
    )
