from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import requests
import streamlit as st


st.set_page_config(page_title="Routing Candidate Workbench", page_icon="🧰", layout="wide")

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
        [p for p in BACKUP_DIR.glob("phase19_routing_candidate_workbench_check_*") if p.is_dir()],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )[:limit]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


st.title("🧰 Phase 19 Routing Candidate Workbench")
st.caption("Read-only candidate workbench foundation. Review writes are not implemented in Step 32.")

st.warning(
    "This page is read-only. It does not save candidate decisions, does not save routing rules, "
    "does not call bridge POST endpoints, and does not call LACRM."
)

status_ok, status = get_json(f"{PLATFORM_API}/front-desk/routing/candidate-workbench/status")
queue_ok, queue = get_json(f"{PLATFORM_API}/front-desk/routing/candidate-workbench/queue?limit=500")

if not status_ok:
    st.error(f"Could not read candidate workbench status: {status}")
    st.stop()

c1, c2, c3, c4 = st.columns(4)
c1.metric("Candidates", status.get("total_candidates", 0))
c2.metric("Eligible", status.get("eligible_for_future_dry_run_import", 0))
c3.metric("Review writes", "Not implemented" if not status.get("review_write_endpoint_implemented") else "CHECK")
c4.metric("Bridge writes", "OFF" if not status.get("bridge_post_enabled") else "CHECK")

if status.get("read_only") and not status.get("review_write_endpoint_implemented") and not status.get("bridge_post_enabled"):
    st.success("Safe workbench confirmed: read-only API, no candidate review writes, no bridge writes.")
else:
    st.error("Review workbench safety flags before continuing.")

st.subheader("Workbench status")
st.json(status)

st.subheader("Candidate queue")
if queue_ok:
    rows = queue.get("candidates", []) if isinstance(queue, dict) else []
    if rows:
        decision_values = sorted({str(row.get("operator_decision") or "unknown") for row in rows})
        selected_decisions = st.multiselect("Decision filter", decision_values, default=decision_values)
        filtered = [row for row in rows if str(row.get("operator_decision") or "unknown") in selected_decisions]
        st.dataframe(filtered, use_container_width=True, hide_index=True)
    else:
        st.info("No routing candidates exist yet. Run the Step 31 dry-run first; execute remains disabled unless explicit gates are set.")
else:
    st.warning(f"Could not read candidate queue: {queue}")

st.subheader("Generated workbench checks")
checks = latest_checks()
if not checks:
    st.info("No workbench check reports found yet. Run `scripts\\phase19_check_routing_candidate_workbench.ps1`.")
else:
    choice = st.selectbox(
        "Workbench check report",
        options=list(range(len(checks))),
        format_func=lambda i: f"{checks[i].name} — {checks[i].stat().st_mtime_ns}",
    )
    check_dir = checks[choice]
    report_path = check_dir / "phase19_routing_candidate_workbench_check.json"
    report = load_json(report_path)
    st.json(report)

st.download_button(
    "Download workbench status JSON",
    json.dumps(status, indent=2, default=str),
    "phase19_routing_candidate_workbench_status.json",
    "application/json",
)

if queue_ok:
    st.download_button(
        "Download candidate queue JSON",
        json.dumps(queue, indent=2, default=str),
        "phase19_routing_candidate_workbench_queue.json",
        "application/json",
    )
