from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

import streamlit as st


st.set_page_config(page_title="Evidence Index", page_icon="🧾", layout="wide")

ROOT = Path(__file__).resolve().parents[2]
WORKSPACE = Path(os.getenv("KPS_WORKSPACE", str(ROOT.parent)))
BACKUP_DIR = WORKSPACE / "backups"

PHONE_RE = re.compile(r"(?<!\w)(?:\+?1[\s\-\.]?)?(?:\(?\d{3}\)?[\s\-\.]?)\d{3}[\s\-\.]?\d{4}(?!\w)")
EMAIL_RE = re.compile(r"(?i)\b[A-Z0-9._%+\-]+@[A-Z0-9.\-]+\.[A-Z]{2,}\b")


def latest_evidence_dirs(limit: int = 20) -> list[Path]:
    if not BACKUP_DIR.exists():
        return []
    return sorted(
        [p for p in BACKUP_DIR.glob("phase19_extractor_evidence_*") if p.is_dir()],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )[:limit]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def has_phone_or_email(text: str) -> tuple[bool, bool]:
    return bool(PHONE_RE.search(text)), bool(EMAIL_RE.search(text))


st.title("🧾 Phase 19 Evidence Index")
st.caption("Read-only viewer for extractor-generated evidence packs.")

st.info(
    "This page reads redacted evidence packs created by the start-here-extractor repo. "
    "It does not call LACRM, does not mutate the platform database, and does not read the live bridge DB."
)

dirs = latest_evidence_dirs()

if not dirs:
    st.warning(
        "No extractor evidence packs found. Run Step 16 option 4 or "
        "`scripts\\phase19_index_release_checkpoint.ps1` in the extractor repo first."
    )
    st.stop()

labels = [f"{p.name} — {p.stat().st_mtime_ns}" for p in dirs]
choice = st.selectbox("Evidence pack", options=list(range(len(dirs))), format_func=lambda i: labels[i])
evidence_dir = dirs[choice]

index_path = evidence_dir / "phase19_evidence_index.json"
summary_path = evidence_dir / "phase19_evidence_summary.json"
redacted_path = evidence_dir / "phase19_redacted_checkpoint.json"

missing = [str(p) for p in [index_path, summary_path, redacted_path] if not p.exists()]
if missing:
    st.error("Evidence pack is incomplete.")
    st.code("\n".join(missing), language="text")
    st.stop()

index = load_json(index_path)
summary = load_json(summary_path)
redacted_text = redacted_path.read_text(encoding="utf-8-sig")
redacted = json.loads(redacted_text)

phone_leak, email_leak = has_phone_or_email(redacted_text)

st.subheader("Evidence safety")
c1, c2, c3, c4 = st.columns(4)
c1.metric("Safety OK", str(bool(index.get("safety_ok"))))
c2.metric("Phone leak check", "CHECK" if phone_leak else "OK")
c3.metric("Email leak check", "CHECK" if email_leak else "OK")
c4.metric("Checkpoint hash", str(index.get("source_checkpoint_sha256", ""))[:12])

if index.get("safety_ok") and not phone_leak and not email_leak:
    st.success("Evidence pack is redacted and safe for review.")
else:
    st.warning("Review evidence redaction and safety flags before sharing this pack.")

st.subheader("Integration summary")
counts = summary.get("integration_counts", {})
safety = summary.get("lacrm_safety", {})
runtime = summary.get("runtime", {})
repo = summary.get("repo_boundaries", {})

m1, m2, m3, m4 = st.columns(4)
m1.metric("FastAPI OK", str(runtime.get("fastapi_health_ok")))
m2.metric("Bridge original UI", str(runtime.get("bridge_original_data_hub")))
m3.metric("SMS messages", counts.get("sms_messages_total", 0))
m4.metric("SMS threads", counts.get("sms_threads_total", 0))

s1, s2, s3, s4 = st.columns(4)
s1.metric("Live enabled", str(safety.get("live_write_enabled")))
s2.metric("Live armed", str(safety.get("live_write_armed")))
s3.metric("Ready live", str(safety.get("ready_for_live_apply")))
s4.metric("Default mode", safety.get("default_mode", "n/a"))

st.subheader("Repository boundary summary")
st.json(repo)

st.subheader("Guardrails")
st.json(summary.get("guardrails", {}))

st.subheader("Evidence files")
st.code(
    "\n".join(
        [
            f"Evidence folder: {evidence_dir}",
            f"Index: {index_path}",
            f"Summary: {summary_path}",
            f"Redacted checkpoint: {redacted_path}",
        ]
    ),
    language="text",
)

with st.expander("Summary JSON", expanded=True):
    st.json(summary)

with st.expander("Redacted checkpoint JSON"):
    st.json(redacted)

st.download_button(
    "Download evidence index JSON",
    json.dumps(index, indent=2, default=str),
    "phase19_evidence_index.json",
    "application/json",
)

st.download_button(
    "Download redacted checkpoint JSON",
    json.dumps(redacted, indent=2, default=str),
    "phase19_redacted_checkpoint.json",
    "application/json",
)
