"""Phase 22 Step 17 read-only planning page.

This page records a Phase 20 network transport planning implementation
preflight packet. It intentionally does not implement transport, create a real
bridge client, open sockets, mutate the platform database, mutate bridge state,
write to LACRM, create operator approval, or create design-closure records.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

STEP_ID = "phase22_step17_phase20_network_transport_planning_implementation_preflight_packet"
STEP_TITLE = "Phase 22 Step 17 - Phase 20 Network Transport Planning Implementation Preflight Packet"
PRIOR_COMPLETED_STEP = "Phase 22 Step 16 - Phase 20 Network Transport Planning Implementation Readiness Packet"
EXPECTED_BRANCH = "phase22-step17-phase20-network-transport-planning-implementation-preflight-packet"

SAFETY_POSTURE: dict[str, Any] = {
    "planning_only": True,
    "platform_db_mutation": False,
    "bridge_mutation": False,
    "real_bridge_http_client": False,
    "network_transport_implementation": False,
    "bridge_post": False,
    "network_sockets": False,
    "execution_implementation": False,
    "implementation_phase_start": False,
    "authorization_record_creation": False,
    "operator_signoff_creation": False,
    "operator_approval_creation": False,
    "final_approval_creation": False,
    "design_closure_record_creation": False,
    "lacrm_default_mode": "dry_run",
    "lacrm_live_write": False,
    "live_write_disabled": True,
    "live_write_unarmed": True,
}


@dataclass(frozen=True)
class PreflightItem:
    area: str
    status: str
    note: str


PREFLIGHT_ITEMS: tuple[PreflightItem, ...] = (
    PreflightItem(
        area="Prior step continuity",
        status="CHECK",
        note="Step 16 implementation readiness packet is treated as completed and committed before Step 17 is applied.",
    ),
    PreflightItem(
        area="Implementation boundary",
        status="PASS",
        note="This preflight packet does not start an implementation phase and does not create execution behavior.",
    ),
    PreflightItem(
        area="Transport boundary",
        status="PASS",
        note="Network transport remains a planning topic only. No network transport implementation is present in this page.",
    ),
    PreflightItem(
        area="Bridge boundary",
        status="PASS",
        note="No real bridge HTTP client, bridge POST, or bridge mutation is introduced.",
    ),
    PreflightItem(
        area="Runtime boundary",
        status="PASS",
        note="No network sockets or runtime server startup are introduced by this preflight packet.",
    ),
    PreflightItem(
        area="LACRM boundary",
        status="PASS",
        note="LACRM default mode remains dry_run. Live write remains disabled and unarmed.",
    ),
    PreflightItem(
        area="Approval boundary",
        status="PASS",
        note="No operator signoff, operator approval, final approval, or design-closure record is created.",
    ),
    PreflightItem(
        area="Platform boundary",
        status="PASS",
        note="No platform database mutation is introduced. This is a read-only planning artifact.",
    ),
)

NON_GOALS: tuple[str, ...] = (
    "Do not create or use a real bridge HTTP client.",
    "Do not implement network transport.",
    "Do not perform a bridge POST.",
    "Do not open network sockets.",
    "Do not start execution implementation.",
    "Do not start an implementation phase.",
    "Do not mutate the platform database.",
    "Do not mutate bridge state.",
    "Do not perform live LACRM write activity.",
    "Do not create operator signoff or operator approval.",
    "Do not create final approval or a design-closure record.",
)


def get_phase22_step17_packet() -> dict[str, Any]:
    """Return the Step 17 packet as a plain data object for tests and UI rendering."""

    return {
        "step_id": STEP_ID,
        "step_title": STEP_TITLE,
        "prior_completed_step": PRIOR_COMPLETED_STEP,
        "expected_branch": EXPECTED_BRANCH,
        "safety_posture": SAFETY_POSTURE,
        "preflight_items": [item.__dict__ for item in PREFLIGHT_ITEMS],
        "non_goals": list(NON_GOALS),
    }


def _get_streamlit():
    try:
        import streamlit as st  # type: ignore
    except Exception:
        return None
    return st


def render_page() -> dict[str, Any]:
    """Render a read-only Streamlit page when Streamlit is available."""

    packet = get_phase22_step17_packet()
    st = _get_streamlit()
    if st is None:
        return packet

    st.set_page_config(page_title="Phase 22 Step 17 Preflight Packet", layout="wide")
    st.title(STEP_TITLE)
    st.caption("Planning-only, no-write, dry_run-safe implementation preflight packet for Phase 20 network transport planning.")

    st.subheader("Boundary posture")
    col_a, col_b, col_c, col_d = st.columns(4)
    col_a.metric("Planning only", "PASS")
    col_b.metric("LACRM default", SAFETY_POSTURE["lacrm_default_mode"])
    col_c.metric("Live write", "disabled and unarmed")
    col_d.metric("Implementation", "not started")

    st.subheader("Preflight checks")
    for item in PREFLIGHT_ITEMS:
        with st.expander(f"{item.status}: {item.area}", expanded=item.status == "CHECK"):
            st.write(item.note)

    st.subheader("Explicit non-goals")
    for non_goal in NON_GOALS:
        st.write(f"- {non_goal}")

    st.subheader("Packet data")
    st.json(packet)
    return packet


render_page()
