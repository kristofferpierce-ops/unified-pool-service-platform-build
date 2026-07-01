from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import streamlit as st


st.set_page_config(page_title="Bridge Parity", page_icon="🧩", layout="wide")

WORKSPACE = Path(os.getenv("KPS_WORKSPACE", r"C:\Users\krist\Desktop\unified_pool_service_platform_build"))
BACKUP_DIR = WORKSPACE / "backups"


def latest_parity_files(limit: int = 20) -> list[Path]:
    if not BACKUP_DIR.exists():
        return []
    return sorted(
        BACKUP_DIR.glob("phase19_bridge_parity_matrix_*.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )[:limit]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


st.title("🧩 Phase 19 Bridge Parity")
st.caption("Read-only matrix of bridge-only, platform-integrated, and future parity capabilities.")

st.info(
    "This page reads generated parity matrix files. It does not call LACRM, "
    "does not mutate platform data, and does not patch the bridge."
)

files = latest_parity_files()
if not files:
    st.warning(
        "No bridge parity matrix found. Run: "
        "`powershell -ExecutionPolicy Bypass -File scripts\\phase19_generate_bridge_parity_matrix.ps1`"
    )
    st.stop()

choice = st.selectbox(
    "Parity matrix",
    options=list(range(len(files))),
    format_func=lambda i: f"{files[i].name} — {files[i].stat().st_mtime_ns}",
)
path = files[choice]
matrix_doc = load_json(path)

runtime = matrix_doc.get("runtime", {})
counts = matrix_doc.get("counts", {})
safety = matrix_doc.get("safety", {})
rows = matrix_doc.get("parity_matrix", [])

c1, c2, c3, c4 = st.columns(4)
c1.metric("FastAPI", "OK" if runtime.get("fastapi_ok") else "Check")
c2.metric("Bridge", "Original UI" if runtime.get("bridge_original_markers", {}).get("data_hub_title") else "Check")
c3.metric("Platform SMS messages", counts.get("platform_sms_messages_total", 0))
c4.metric("Live writes", "OFF" if not safety.get("live_write_enabled") and not safety.get("live_write_armed") else "CHECK")

st.subheader("Capability matrix")
if rows:
    st.dataframe(rows, use_container_width=True, hide_index=True)
else:
    st.warning("No parity rows in manifest.")

st.subheader("Bridge original UI markers")
st.json(runtime.get("bridge_original_markers", {}))

st.subheader("Next recommended slices")
for item in matrix_doc.get("next_recommended_slices", []):
    st.markdown(f"- {item}")

with st.expander("Raw parity matrix JSON"):
    st.json(matrix_doc)

st.download_button(
    "Download parity matrix JSON",
    json.dumps(matrix_doc, indent=2, default=str),
    "phase19_bridge_parity_matrix.json",
    "application/json",
)
