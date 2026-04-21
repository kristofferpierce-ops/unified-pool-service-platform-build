from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import requests
import streamlit as st


st.set_page_config(page_title="Routing Candidate Import", page_icon="🚦", layout="wide")

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


def latest_runs(limit: int = 20) -> list[Path]:
    if not BACKUP_DIR.exists():
        return []
    return sorted(
        [p for p in BACKUP_DIR.glob("phase19_routing_candidate_import_run_*") if p.is_dir()],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )[:limit]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


st.title("🚦 Phase 19 Routing Candidate Import")
st.caption("Disabled-by-default candidate importer. Dry-run is the safe default.")

st.warning(
    "This page is status/report only. It does not trigger imports. Use the Step 31 script for a dry-run, "
    "and keep execution disabled unless explicit gates are intentionally configured."
)

status_ok, status = get_json(f"{PLATFORM_API}/front-desk/routing/candidates/import/status")
if not status_ok:
    st.error(f"Could not read routing candidate import status: {status}")
    st.stop()

c1, c2, c3, c4 = st.columns(4)
c1.metric("Default", status.get("safe_default", "unknown"))
c2.metric("Import enabled", str(bool(status.get("candidate_import_enabled"))))
c3.metric("Import armed", str(bool(status.get("candidate_import_armed"))))
c4.metric("Bridge writes", "OFF" if not status.get("bridge_post_enabled") else "CHECK")

if not status.get("candidate_import_enabled") and not status.get("candidate_import_armed") and not status.get("bridge_post_enabled"):
    st.success("Safe default confirmed: importer disabled, unarmed, and no bridge write path.")
else:
    st.warning("Importer gates are not fully disabled. Confirm this is intentional before running any execute flow.")

st.subheader("Import gate status")
st.json(status)

st.subheader("How to run safe dry-run")
st.code(
    "powershell -ExecutionPolicy Bypass -File scripts\\phase19_run_routing_candidate_import.ps1",
    language="powershell",
)

st.subheader("Generated import runs")
runs = latest_runs()
if not runs:
    st.info("No routing candidate import run reports found yet.")
else:
    choice = st.selectbox(
        "Import run",
        options=list(range(len(runs))),
        format_func=lambda i: f"{runs[i].name} — {runs[i].stat().st_mtime_ns}",
    )
    run_dir = runs[choice]
    json_path = run_dir / "phase19_routing_candidate_import_run.json"
    csv_path = run_dir / "phase19_routing_candidate_import_run.csv"
    report = load_json(json_path)

    st.json(report.get("safety", {}))
    rows = report.get("import_rows", [])
    if rows:
        st.dataframe(rows, use_container_width=True, hide_index=True)

    if csv_path.exists():
        st.download_button(
            "Download import run CSV",
            csv_path.read_text(encoding="utf-8-sig"),
            "phase19_routing_candidate_import_run.csv",
            "text/csv",
        )

    st.download_button(
        "Download import run JSON",
        json.dumps(report, indent=2, default=str),
        "phase19_routing_candidate_import_run.json",
        "application/json",
    )
