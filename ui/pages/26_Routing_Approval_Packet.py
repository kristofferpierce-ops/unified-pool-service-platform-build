from __future__ import annotations

import csv
import json
import os
from pathlib import Path
from typing import Any

import streamlit as st


st.set_page_config(page_title="Routing Approval Packet", page_icon="📋", layout="wide")

WORKSPACE = Path(os.getenv("KPS_WORKSPACE", r"C:\Users\krist\Desktop\unified_pool_service_platform_build"))
BACKUP_DIR = WORKSPACE / "backups"


def latest_packets(limit: int = 20) -> list[Path]:
    if not BACKUP_DIR.exists():
        return []
    return sorted(
        [p for p in BACKUP_DIR.glob("phase19_routing_approval_packet_*") if p.is_dir()],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )[:limit]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


st.title("📋 Phase 19 Routing Approval Packet")
st.caption("Operator review packet for dry-run bridge routing migration candidates.")

st.warning(
    "This page is packet-only. It does not save routing rules, does not write platform preferences, "
    "does not call bridge POST endpoints, and does not call LACRM."
)

packets = latest_packets()
if not packets:
    st.info(
        "No routing approval packet found yet. Run "
        "`scripts\\phase19_generate_routing_approval_packet.ps1` from the platform repo."
    )
    st.stop()

choice = st.selectbox(
    "Approval packet",
    options=list(range(len(packets))),
    format_func=lambda i: f"{packets[i].name} — {packets[i].stat().st_mtime_ns}",
)
packet_dir = packets[choice]
json_path = packet_dir / "phase19_routing_approval_packet.json"
csv_path = packet_dir / "phase19_routing_approval_packet.csv"
md_path = packet_dir / "phase19_routing_approval_packet.md"

packet = load_json(json_path)
safety = packet.get("safety", {})
counts = packet.get("counts", {})
rows = packet.get("packet_rows", [])

c1, c2, c3, c4 = st.columns(4)
c1.metric("Packet rows", counts.get("packet_rows", len(rows)))
c2.metric("Packet only", str(bool(safety.get("packet_only"))))
c3.metric("Bridge writes", "OFF" if not safety.get("bridge_mutation_performed") else "CHECK")
c4.metric("Routing write endpoint", "Not implemented" if not safety.get("routing_write_endpoint_implemented") else "CHECK")

if safety.get("packet_only") and not safety.get("platform_db_mutation_performed") and not safety.get("bridge_mutation_performed"):
    st.success("Safe packet confirmed: no platform DB write and no bridge mutation.")
else:
    st.error("Review packet safety flags before continuing.")

st.subheader("Risk summary")
st.json(counts.get("risk_counts", {}))

st.subheader("Approval recommendation summary")
st.json(counts.get("approval_recommendation_counts", {}))

st.subheader("Review instructions")
for item in packet.get("review_instructions", []):
    st.markdown(f"- {item}")

st.subheader("Approval packet rows")
if rows:
    risk_values = sorted({str(row.get("risk_level") or "unknown") for row in rows})
    selected_risks = st.multiselect("Risk filter", risk_values, default=risk_values)

    recommendation_values = sorted({str(row.get("approval_recommendation") or "unknown") for row in rows})
    selected_recommendations = st.multiselect("Recommendation filter", recommendation_values, default=recommendation_values)

    filtered = [
        row for row in rows
        if str(row.get("risk_level") or "unknown") in selected_risks
        and str(row.get("approval_recommendation") or "unknown") in selected_recommendations
    ]

    st.dataframe(filtered, use_container_width=True, hide_index=True)
else:
    st.info("No packet rows were generated.")

st.subheader("Packet files")
st.code(
    "\n".join(
        [
            f"Folder: {packet_dir}",
            f"JSON: {json_path}",
            f"CSV: {csv_path}",
            f"Markdown: {md_path}",
        ]
    ),
    language="text",
)

if csv_path.exists():
    st.download_button(
        "Download routing approval CSV",
        csv_path.read_text(encoding="utf-8-sig"),
        "phase19_routing_approval_packet.csv",
        "text/csv",
    )

st.download_button(
    "Download routing approval JSON",
    json.dumps(packet, indent=2, default=str),
    "phase19_routing_approval_packet.json",
    "application/json",
)

with st.expander("Raw packet JSON"):
    st.json(packet)
