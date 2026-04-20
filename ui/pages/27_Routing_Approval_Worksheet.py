from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st


st.set_page_config(page_title="Routing Approval Worksheet", page_icon="📝", layout="wide")

WORKSPACE = Path(os.getenv("KPS_WORKSPACE", r"C:\Users\krist\Desktop\unified_pool_service_platform_build"))
BACKUP_DIR = WORKSPACE / "backups"

ALLOWED_DECISIONS = [
    "unreviewed",
    "candidate_keep_manual",
    "needs_contact_verification",
    "needs_scope_review",
    "block_until_reviewed",
    "approved_for_future_dry_run_only",
    "skip",
]


def latest_worksheets(limit: int = 20) -> list[Path]:
    if not BACKUP_DIR.exists():
        return []
    return sorted(
        [p for p in BACKUP_DIR.glob("phase19_routing_approval_worksheet_*") if p.is_dir()],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )[:limit]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


st.title("📝 Phase 19 Routing Approval Worksheet")
st.caption("Editable review worksheet for routing candidates. Download-only; no database or bridge writes.")

st.warning(
    "This page is worksheet-only. It does not save routing rules, does not write platform preferences, "
    "does not call bridge POST endpoints, and does not call LACRM. Use downloads for review handoff."
)

worksheets = latest_worksheets()
if not worksheets:
    st.info(
        "No routing approval worksheet found yet. Run "
        "`scripts\\phase19_generate_routing_approval_worksheet.ps1` from the platform repo."
    )
    st.stop()

choice = st.selectbox(
    "Approval worksheet",
    options=list(range(len(worksheets))),
    format_func=lambda i: f"{worksheets[i].name} — {worksheets[i].stat().st_mtime_ns}",
)
worksheet_dir = worksheets[choice]
json_path = worksheet_dir / "phase19_routing_approval_worksheet.json"
csv_path = worksheet_dir / "phase19_routing_approval_worksheet.csv"
md_path = worksheet_dir / "phase19_routing_approval_worksheet.md"

worksheet = load_json(json_path)
safety = worksheet.get("safety", {})
counts = worksheet.get("counts", {})
rows = worksheet.get("worksheet_rows", [])

c1, c2, c3, c4 = st.columns(4)
c1.metric("Worksheet rows", counts.get("worksheet_rows", len(rows)))
c2.metric("Worksheet only", str(bool(safety.get("worksheet_only"))))
c3.metric("Bridge writes", "OFF" if not safety.get("bridge_mutation_performed") else "CHECK")
c4.metric("Routing write endpoint", "Not implemented" if not safety.get("routing_write_endpoint_implemented") else "CHECK")

if safety.get("worksheet_only") and not safety.get("platform_db_mutation_performed") and not safety.get("bridge_mutation_performed"):
    st.success("Safe worksheet confirmed: no platform DB write and no bridge mutation.")
else:
    st.error("Review worksheet safety flags before continuing.")

st.subheader("Default decision summary")
st.json(counts.get("default_decision_counts", {}))

st.subheader("Risk summary")
st.json(counts.get("risk_counts", {}))

st.subheader("Editable worksheet")
if rows:
    df = pd.DataFrame(rows)
    editable_cols = ["operator_decision", "operator_notes"]
    visible_cols = [
        "phone",
        "risk_level",
        "proposed_action",
        "approval_recommendation",
        "default_decision",
        "operator_decision",
        "operator_notes",
        "proposed_mode",
        "proposed_owner_type",
        "batch_count",
        "default_contact_count",
        "write_status",
        "decision_reason",
    ]
    existing_cols = [col for col in visible_cols if col in df.columns]

    edited = st.data_editor(
        df[existing_cols],
        use_container_width=True,
        hide_index=True,
        column_config={
            "operator_decision": st.column_config.SelectboxColumn(
                "operator_decision",
                options=ALLOWED_DECISIONS,
                help="Download-only review decision. This does not write to platform or bridge.",
            ),
            "operator_notes": st.column_config.TextColumn(
                "operator_notes",
                help="Download-only review notes.",
            ),
        },
        disabled=[col for col in existing_cols if col not in editable_cols],
        num_rows="fixed",
    )

    st.download_button(
        "Download edited worksheet CSV",
        edited.to_csv(index=False),
        "phase19_routing_approval_worksheet_edited.csv",
        "text/csv",
    )

    st.download_button(
        "Download edited worksheet JSON",
        edited.to_json(orient="records", indent=2),
        "phase19_routing_approval_worksheet_edited.json",
        "application/json",
    )
else:
    st.info("No worksheet rows were generated.")

st.subheader("Worksheet files")
st.code(
    "\n".join(
        [
            f"Folder: {worksheet_dir}",
            f"JSON: {json_path}",
            f"CSV: {csv_path}",
            f"Markdown: {md_path}",
        ]
    ),
    language="text",
)

if csv_path.exists():
    st.download_button(
        "Download original worksheet CSV",
        csv_path.read_text(encoding="utf-8-sig"),
        "phase19_routing_approval_worksheet.csv",
        "text/csv",
    )

with st.expander("Raw worksheet JSON"):
    st.json(worksheet)
