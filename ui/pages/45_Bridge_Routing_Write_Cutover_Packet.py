from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import streamlit as st


st.set_page_config(page_title="Bridge Routing Write Cutover Packet", page_icon="📦", layout="wide")

WORKSPACE = Path(os.getenv("KPS_WORKSPACE", r"C:\Users\krist\Desktop\unified_pool_service_platform_build"))
BACKUP_DIR = WORKSPACE / "backups"


def latest_packets(limit: int = 20) -> list[Path]:
    if not BACKUP_DIR.exists():
        return []
    return sorted(
        [
            p
            for p in BACKUP_DIR.glob("phase19_bridge_routing_write_cutover_packet_*")
            if p.is_dir() and (p / "phase19_bridge_routing_write_cutover_packet.json").exists()
        ],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )[:limit]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


st.title("📦 Phase 19 Bridge Routing Write Cutover Packet")
st.caption("Operator-review packet for future guarded bridge routing write design.")

st.warning(
    "This page is cutover-packet-only. It does not write to the bridge, does not save platform records, "
    "does not call bridge POST endpoints, and does not call LACRM."
)

packets = latest_packets()
if not packets:
    st.info(
        "No bridge routing write cutover packet found yet. Run "
        "`scripts\\phase19_generate_bridge_routing_write_cutover_packet.ps1` from the platform repo."
    )
    st.stop()

choice = st.selectbox(
    "Cutover packet",
    options=list(range(len(packets))),
    format_func=lambda i: f"{packets[i].name} — {packets[i].stat().st_mtime_ns}",
)
packet_dir = packets[choice]
json_path = packet_dir / "phase19_bridge_routing_write_cutover_packet.json"
checklist_csv_path = packet_dir / "phase19_bridge_routing_write_cutover_packet_checklist.csv"
artifacts_csv_path = packet_dir / "phase19_bridge_routing_write_cutover_packet_artifacts.csv"
md_path = packet_dir / "phase19_bridge_routing_write_cutover_packet.md"

packet = load_json(json_path)
safety = packet.get("safety", {})
cutover = packet.get("cutover_packet", {})
checklist = packet.get("checklist", [])
artifacts = packet.get("artifacts", {})
safety_blockers = packet.get("safety_blockers", [])

c1, c2, c3, c4 = st.columns(4)
c1.metric("Packet status", cutover.get("status", "unknown"))
c2.metric("Required failures", cutover.get("required_failures", 0))
c3.metric("Safety blockers", cutover.get("safety_blockers", 0))
c4.metric("Bridge POST", "Not called" if not safety.get("bridge_post_called") else "CHECK")

if (
    safety.get("bridge_routing_write_cutover_packet_only")
    and not safety.get("platform_db_mutation_performed")
    and not safety.get("bridge_post_called")
    and not safety.get("bridge_write_implementation_added")
):
    st.success("Safe cutover packet confirmed: no platform DB write, no bridge POST, no bridge write implementation.")
else:
    st.error("Review cutover packet safety flags before continuing.")

if cutover.get("status") == "blocked":
    st.error("Cutover packet is blocked. Resolve required failures before future bridge-write design.")
elif cutover.get("status") == "operator_review_required":
    st.warning("Operator review is required before future bridge-write design.")
else:
    st.success("Packet is ready for future guarded-write design review. This still does not allow execution.")

st.subheader("Cutover packet summary")
st.json(cutover)

st.subheader("Artifacts")
if artifacts:
    artifact_rows = []
    for key, value in artifacts.items():
        row = {"key": key}
        if isinstance(value, dict):
            row.update(value)
        artifact_rows.append(row)
    st.dataframe(artifact_rows, use_container_width=True, hide_index=True)
else:
    st.info("No artifacts were recorded.")

st.subheader("Checklist")
if checklist:
    category_values = sorted({str(row.get("category") or "unknown") for row in checklist})
    selected_categories = st.multiselect("Category filter", category_values, default=category_values)
    filtered = [row for row in checklist if str(row.get("category") or "unknown") in selected_categories]
    st.dataframe(filtered, use_container_width=True, hide_index=True)
else:
    st.info("No checklist items were recorded.")

st.subheader("Safety blockers")
if safety_blockers:
    st.error("Safety blockers were recorded.")
    st.code("\n".join(str(x) for x in safety_blockers), language="text")
else:
    st.success("No safety blockers were recorded.")

st.subheader("Operator signoff")
st.json(packet.get("operator_signoff", {}))

st.subheader("Report files")
st.code(
    "\n".join(
        [
            f"Folder: {packet_dir}",
            f"JSON: {json_path}",
            f"Checklist CSV: {checklist_csv_path}",
            f"Artifacts CSV: {artifacts_csv_path}",
            f"Markdown: {md_path}",
        ]
    ),
    language="text",
)

if checklist_csv_path.exists():
    st.download_button(
        "Download checklist CSV",
        checklist_csv_path.read_text(encoding="utf-8-sig"),
        "phase19_bridge_routing_write_cutover_packet_checklist.csv",
        "text/csv",
    )

if artifacts_csv_path.exists():
    st.download_button(
        "Download artifacts CSV",
        artifacts_csv_path.read_text(encoding="utf-8-sig"),
        "phase19_bridge_routing_write_cutover_packet_artifacts.csv",
        "text/csv",
    )

st.download_button(
    "Download cutover packet JSON",
    json.dumps(packet, indent=2, default=str),
    "phase19_bridge_routing_write_cutover_packet.json",
    "application/json",
)

with st.expander("Raw cutover packet JSON"):
    st.json(packet)
