from __future__ import annotations

import json
import os
import socket
import subprocess
from pathlib import Path

import requests
import streamlit as st


st.set_page_config(page_title="Environment Health", page_icon="🛠️", layout="wide")

ROOT = Path(__file__).resolve().parents[2]
PLATFORM_API = os.getenv("PLATFORM_API_BASE_URL", "http://127.0.0.1:8010")
STREAMLIT_URL = os.getenv("PLATFORM_STREAMLIT_URL", "http://127.0.0.1:8501")
BRIDGE_URL = os.getenv("BRIDGE_URL", "http://127.0.0.1:8000")


def port_open(port: int) -> bool:
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=0.8):
            return True
    except OSError:
        return False


def get_json(url: str) -> tuple[bool, dict | str]:
    try:
        r = requests.get(url, timeout=5)
        r.raise_for_status()
        return True, r.json()
    except Exception as exc:
        return False, str(exc)


def get_text(url: str) -> tuple[bool, str]:
    try:
        r = requests.get(url, timeout=5)
        r.raise_for_status()
        return True, r.text
    except Exception as exc:
        return False, str(exc)


def git_value(args: list[str]) -> str:
    try:
        completed = subprocess.run(["git", *args], cwd=str(ROOT), capture_output=True, text=True, check=False)
        return (completed.stdout or completed.stderr).strip()
    except Exception as exc:
        return str(exc)


st.title("🛠️ Phase 19 Environment Health")
st.caption("Read-only local stack checks for FastAPI, Streamlit, and the KPS Bridge.")
st.info("Correct local map: Streamlit dashboard on 8501, FastAPI backend on 8010, and the original KPS Bridge / Data Hub UI on 8000.")

api_ok, api_health = get_json(f"{PLATFORM_API}/health")
ing_ok, ingestion = get_json(f"{PLATFORM_API}/connectors/ringcentral/ingestion-status")
safety_ok, safety = get_json(f"{PLATFORM_API}/front-desk/lacrm-apply/status")
bridge_ok, bridge_html = get_text(BRIDGE_URL)

bridge_original = bridge_ok and "Keys Pool Service Data Hub" in bridge_html and "incomingHud" in bridge_html
live_off = safety_ok and not safety.get("live_write_enabled") and not safety.get("live_write_armed")

c1, c2, c3, c4 = st.columns(4)
c1.metric("FastAPI 8010", "OK" if api_ok and port_open(8010) else "Check")
c2.metric("Streamlit 8501", "OK" if port_open(8501) else "Check")
c3.metric("Bridge 8000", "OK" if bridge_original and port_open(8000) else "Check")
c4.metric("Live LACRM writes", "OFF" if live_off else "CHECK")

st.subheader("Integration counts")
if ing_ok and isinstance(ingestion, dict):
    i1, i2, i3 = st.columns(3)
    i1.metric("Raw RingCentral records", ingestion.get("raw_total", 0))
    i2.metric("SMS threads", ingestion.get("sms_threads_total", 0))
    i3.metric("SMS messages", ingestion.get("sms_messages_total", 0))
else:
    st.warning(f"Could not load ingestion status: {ingestion}")

st.subheader("Safety")
if safety_ok and isinstance(safety, dict):
    s1, s2, s3, s4 = st.columns(4)
    s1.metric("LACRM key", "Configured" if safety.get("lacrm_api_key_configured") else "Missing")
    s2.metric("Live enabled", str(bool(safety.get("live_write_enabled"))))
    s3.metric("Live armed", str(bool(safety.get("live_write_armed"))))
    s4.metric("Default mode", safety.get("default_mode", "dry_run"))
    if live_off:
        st.success("Live LACRM writes are off and unarmed.")
    else:
        st.error("Review live-write flags before continuing.")
else:
    st.warning(f"Could not load safety status: {safety}")

st.subheader("Git")
col1, col2 = st.columns(2)
col1.code(git_value(["branch", "--show-current"]) or "unknown", language="text")
col2.code(git_value(["status", "--short"]) or "working tree clean", language="text")

st.subheader("Repair / start commands")
st.code(
    "powershell -ExecutionPolicy Bypass -File scripts\\phase19_repair_platform_venv.ps1\n"
    "powershell -ExecutionPolicy Bypass -File scripts\\phase19_start_local_stack.ps1\n"
    "powershell -ExecutionPolicy Bypass -File scripts\\phase19_verify_local_stack.ps1\n"
    "powershell -ExecutionPolicy Bypass -File scripts\\phase19_stop_local_stack.ps1",
    language="powershell",
)

payload = {
    "api_ok": api_ok,
    "bridge_original": bridge_original,
    "streamlit_port": port_open(8501),
    "ingestion": ingestion if isinstance(ingestion, dict) else {"error": ingestion},
    "safety": safety if isinstance(safety, dict) else {"error": safety},
    "git_branch": git_value(["branch", "--show-current"]),
}
st.download_button("Download environment health JSON", json.dumps(payload, indent=2, default=str), "phase19_environment_health.json", "application/json")
