from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

import streamlit as st


st.set_page_config(page_title="Integration Manifest", page_icon="🧭", layout="wide")

WORKSPACE = Path(os.getenv("KPS_WORKSPACE", r"C:\Users\krist\Desktop\unified_pool_service_platform_build"))
BACKUP_DIR = WORKSPACE / "backups"

SECRET_MARKERS = [
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


def latest_manifests(limit: int = 20) -> list[Path]:
    if not BACKUP_DIR.exists():
        return []
    return sorted(
        BACKUP_DIR.glob("phase19_integration_manifest_*.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )[:limit]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


st.title("🧭 Phase 19 Integration Manifest")
st.caption("Read-only cross-repo manifest for platform, bridge, and extractor integration state.")

st.info(
    "This page reads generated manifest files only. It does not call LACRM, "
    "does not mutate platform data, and does not read the live bridge database."
)

manifests = latest_manifests()
if not manifests:
    st.warning(
        "No integration manifest found. Run: "
        "`powershell -ExecutionPolicy Bypass -File scripts\\phase19_generate_integration_manifest.ps1`"
    )
    st.stop()

choice = st.selectbox(
    "Manifest",
    options=list(range(len(manifests))),
    format_func=lambda i: f"{manifests[i].name} — {manifests[i].stat().st_mtime_ns}",
)
path = manifests[choice]
manifest = load_json(path)

runtime = manifest.get("runtime", {})
integration = manifest.get("integration", {})
safety = manifest.get("lacrm_safety", {})
repos = manifest.get("repos", {})
evidence = manifest.get("evidence", {})
guardrails = manifest.get("guardrails", {})

st.subheader("App map")
st.json(manifest.get("app_map", {}))

c1, c2, c3, c4 = st.columns(4)
c1.metric("FastAPI", "OK" if runtime.get("fastapi_ok") else "Check")
c2.metric("Streamlit", "OK" if runtime.get("streamlit_ok") else "Check")
c3.metric("Bridge", "Original UI" if runtime.get("bridge_original_data_hub") else "Check")
c4.metric("Ready next phase", str(bool(guardrails.get("ready_for_next_phase"))))

st.subheader("Integration and safety")
m1, m2, m3, m4 = st.columns(4)
m1.metric("SMS messages", integration.get("sms_messages_total", 0))
m2.metric("SMS threads", integration.get("sms_threads_total", 0))
m3.metric("Live enabled", str(safety.get("live_write_enabled")))
m4.metric("Live armed", str(safety.get("live_write_armed")))

if not safety.get("live_write_enabled") and not safety.get("live_write_armed"):
    st.success("LACRM live writes remain off.")
else:
    st.error("Review live-write safety before continuing.")

st.subheader("Repository branches")
repo_rows = []
for name in ["platform", "bridge_repo", "extractor", "bridge_live_folder"]:
    info = repos.get(name, {}) if isinstance(repos.get(name), dict) else {}
    repo_rows.append(
        {
            "repo": name,
            "is_git_repo": info.get("is_git_repo"),
            "branch": info.get("branch"),
            "head": info.get("head"),
            "path": info.get("path"),
        }
    )
st.dataframe(repo_rows, use_container_width=True, hide_index=True)

with st.expander("Repository status details"):
    st.json(repos)

st.subheader("Evidence")
st.code(
    "\n".join(
        [
            f"Release checkpoint: {evidence.get('latest_release_checkpoint', '')}",
            f"Evidence index: {evidence.get('latest_extractor_evidence_index', '')}",
            f"Evidence safety OK: {evidence.get('evidence_safety_ok')}",
            f"Evidence index version: {evidence.get('evidence_index_version', '')}",
        ]
    ),
    language="text",
)

st.subheader("Commit guardrails")
blocked = guardrails.get("platform_blocked_patterns_visible") or []
if blocked:
    st.warning("The platform working tree still shows local/runtime or unrelated items. Do not stage these in Phase 19 commits.")
    st.code("\n".join(blocked), language="text")
else:
    st.success("No known blocked platform status markers are visible in the manifest.")

st.code(
    "\n".join(
        [
            "Do not stage: data/unified_pool_service_platform.db",
            "Do not stage: .env / .venv",
            "Do not stage: front_desk_bridge / front_desk_bridge_repo",
            "Do not stage: generated backups/evidence packs",
            "Do not stage: Replaster Quote files unless on their own feature branch",
        ]
    ),
    language="text",
)

with st.expander("Raw manifest JSON"):
    st.json(manifest)

st.download_button(
    "Download integration manifest JSON",
    json.dumps(manifest, indent=2, default=str),
    "phase19_integration_manifest.json",
    "application/json",
)
