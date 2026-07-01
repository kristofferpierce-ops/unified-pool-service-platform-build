from __future__ import annotations

import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests
import streamlit as st


st.set_page_config(page_title="Release Checkpoint", page_icon="📦", layout="wide")

ROOT = Path(__file__).resolve().parents[2]
WORKSPACE = ROOT.parent
PLATFORM_API = os.getenv("PLATFORM_API_BASE_URL", "http://127.0.0.1:8010")
STREAMLIT_URL = os.getenv("PLATFORM_STREAMLIT_URL", "http://127.0.0.1:8501")
BRIDGE_URL = os.getenv("BRIDGE_URL", "http://127.0.0.1:8000")

BLOCKED_STATUS_MARKERS = [
    "data/unified_pool_service_platform.db",
    ".env",
    ".venv",
    "front_desk_bridge",
    "front_desk_bridge_repo",
    "app/services/replaster_quote.py",
    "docs/26_REPLASTER_QUOTE_TOOL_PLAN.md",
    "tests/test_replaster_quote.py",
    "ui/pages/13_Replaster_Quote.py",
]


def get_json(url: str) -> tuple[bool, dict[str, Any] | str]:
    try:
        r = requests.get(url, timeout=8)
        r.raise_for_status()
        return True, r.json()
    except Exception as exc:  # pragma: no cover - runtime diagnostic display
        return False, str(exc)


def get_text(url: str) -> tuple[bool, str]:
    try:
        r = requests.get(url, timeout=8)
        r.raise_for_status()
        return True, r.text
    except Exception as exc:  # pragma: no cover - runtime diagnostic display
        return False, str(exc)


def git_lines(path: Path, args: list[str]) -> list[str]:
    if not (path / ".git").exists():
        return ["not a git repo"]
    try:
        completed = subprocess.run(["git", *args], cwd=str(path), capture_output=True, text=True, check=False)
        text = completed.stdout.strip() or completed.stderr.strip()
        return text.splitlines() if text else []
    except Exception as exc:  # pragma: no cover
        return [str(exc)]


def git_info(path: Path) -> dict[str, Any]:
    return {
        "path": str(path),
        "is_git_repo": (path / ".git").exists(),
        "branch": "\n".join(git_lines(path, ["branch", "--show-current"])),
        "status_short": git_lines(path, ["status", "--short"]),
        "remote": git_lines(path, ["remote", "-v"]),
    }


def has_blocked_platform_items(status_lines: list[str]) -> list[str]:
    joined = "\n".join(status_lines)
    return [marker for marker in BLOCKED_STATUS_MARKERS if marker in joined]


st.title("📦 Phase 19 Release Checkpoint")
st.caption("Read-only checkpoint for the platform / bridge / extractor integration state.")

st.info(
    "Correct app map: Streamlit dashboard on 8501, FastAPI backend/API on 8010, "
    "and the original KPS Bridge / Data Hub UI on 8000."
)

api_ok, api_health = get_json(f"{PLATFORM_API}/health")
ing_ok, ingestion = get_json(f"{PLATFORM_API}/connectors/ringcentral/ingestion-status")
safety_ok, safety = get_json(f"{PLATFORM_API}/front-desk/lacrm-apply/status")
live_ok, live_readiness = get_json(f"{PLATFORM_API}/front-desk/lacrm-apply/live-readiness")
text_ok, text_quality = get_json(f"{PLATFORM_API}/front-desk/text-quality/summary?sample_limit=5")
bridge_ok, bridge_html = get_text(BRIDGE_URL)
streamlit_ok, _streamlit_html = get_text(STREAMLIT_URL)

bridge_original = bridge_ok and "Keys Pool Service Data Hub" in bridge_html and "incomingHud" in bridge_html
live_off = safety_ok and isinstance(safety, dict) and not safety.get("live_write_enabled") and not safety.get("live_write_armed")
ready_for_live = live_ok and isinstance(live_readiness, dict) and bool(live_readiness.get("ready_for_live_apply"))

platform_git = git_info(ROOT)
bridge_git = git_info(WORKSPACE / "front_desk_bridge_repo")
extractor_git = git_info(WORKSPACE / "start_here_extractor_m1_completion")
blocked_items = has_blocked_platform_items(platform_git["status_short"])

c1, c2, c3, c4 = st.columns(4)
c1.metric("FastAPI 8010", "OK" if api_ok else "Check")
c2.metric("Streamlit 8501", "OK" if streamlit_ok else "Check")
c3.metric("Bridge 8000", "Original UI" if bridge_original else "Check")
c4.metric("Live LACRM writes", "OFF" if live_off else "CHECK")

st.subheader("Release readiness")
r1, r2, r3, r4 = st.columns(4)
if isinstance(ingestion, dict):
    r1.metric("SMS messages", ingestion.get("sms_messages_total", 0))
    r2.metric("SMS threads", ingestion.get("sms_threads_total", 0))
else:
    r1.metric("SMS messages", "n/a")
    r2.metric("SMS threads", "n/a")
if isinstance(safety, dict):
    r3.metric("Dry-run actions", safety.get("status_counts", {}).get("dry_run", 0))
else:
    r3.metric("Dry-run actions", "n/a")
r4.metric("Ready for live apply", str(ready_for_live))

if live_off and not ready_for_live:
    st.success("Safe default confirmed: live LACRM writes are off and the platform is not ready for live apply.")
else:
    st.error("Review LACRM live-write readiness before continuing.")

if blocked_items:
    st.warning(
        "Working tree contains local/runtime or unrelated items that should not be staged in Phase 19 commits: "
        + ", ".join(blocked_items)
    )
else:
    st.success("No known blocked local/runtime patterns detected in platform git status.")

st.subheader("Repository boundaries")
repo_cols = st.columns(3)
for col, title, info in [
    (repo_cols[0], "Platform repo", platform_git),
    (repo_cols[1], "Bridge repo copy", bridge_git),
    (repo_cols[2], "Extractor repo", extractor_git),
]:
    col.markdown(f"**{title}**")
    col.code(info.get("branch") or "not available", language="text")
    with col.expander("Status"):
        col.code("\n".join(info.get("status_short") or ["clean"]), language="text")

st.subheader("What should not be committed")
st.code(
    "\n".join(
        [
            "data/unified_pool_service_platform.db",
            ".env / .env.*",
            ".venv/",
            "front_desk_bridge/",
            "front_desk_bridge_repo/",
            "backups/",
            "Replaster Quote files unless on their own branch",
        ]
    ),
    language="text",
)

st.subheader("Checkpoint export command")
st.code(
    "powershell -ExecutionPolicy Bypass -File scripts\\phase19_export_release_checkpoint.ps1",
    language="powershell",
)

payload = {
    "generated_at": datetime.now(timezone.utc).isoformat(),
    "app_map": {"streamlit": STREAMLIT_URL, "fastapi": PLATFORM_API, "bridge": BRIDGE_URL},
    "runtime": {"api_ok": api_ok, "streamlit_ok": streamlit_ok, "bridge_original": bridge_original},
    "ingestion": ingestion if isinstance(ingestion, dict) else {"error": ingestion},
    "text_quality": text_quality if isinstance(text_quality, dict) else {"error": text_quality},
    "safety": safety if isinstance(safety, dict) else {"error": safety},
    "live_readiness": live_readiness if isinstance(live_readiness, dict) else {"error": live_readiness},
    "git": {"platform": platform_git, "bridge_repo": bridge_git, "extractor": extractor_git},
    "blocked_items": blocked_items,
}
st.download_button(
    "Download release checkpoint JSON",
    json.dumps(payload, indent=2, default=str),
    "phase19_release_checkpoint.json",
    "application/json",
)
