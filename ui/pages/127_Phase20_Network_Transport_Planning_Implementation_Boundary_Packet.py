"""Phase 22 Step 21 planning boundary packet page.

This Streamlit page is intentionally read-only. It summarizes the Phase 20
network transport planning implementation boundary posture without starting
network transport implementation or runtime work.
"""

from __future__ import annotations

from pathlib import Path

try:
    import streamlit as st
except Exception:  # pragma: no cover
    st = None


TITLE = "Phase 22 Step 21 - Phase 20 Network Transport Planning Implementation Boundary Packet"

SAFETY_FLAGS = {
    "planning_only": True,
    "no_platform_db_mutation": True,
    "no_bridge_mutation": True,
    "no_real_bridge_http_client": True,
    "no_network_transport_implementation": True,
    "no_bridge_post": True,
    "no_network_sockets": True,
    "no_execution_implementation": True,
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
    "boundary_mode": "planning_boundary_only",
}


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def step_files() -> list[str]:
    return [
        "scripts/phase22_generate_phase20_network_transport_planning_implementation_boundary_packet.ps1",
        "ui/pages/127_Phase20_Network_Transport_Planning_Implementation_Boundary_Packet.py",
        "docs/PHASE22_STEP21_PHASE20_NETWORK_TRANSPORT_PLANNING_IMPLEMENTATION_BOUNDARY_PACKET.md",
        "tests/test_phase22_phase20_network_transport_planning_implementation_boundary_packet.py",
    ]


def render() -> None:
    if st is None:
        return

    st.set_page_config(page_title="Phase 22 Step 21 Boundary Packet", layout="wide")
    st.title(TITLE)
    st.caption("Read-only planning checkpoint. No runtime transport work is started here.")

    st.subheader("Boundary posture")
    st.write(
        "This packet records the implementation boundary before any future network "
        "transport execution work. It does not approve, start, or implement transport."
    )

    st.subheader("Safety posture")
    st.json(SAFETY_FLAGS)

    st.subheader("Step files")
    root = repo_root()
    for relative in step_files():
        path = root / relative
        st.write(f"{'PRESENT' if path.exists() else 'MISSING'}: `{relative}`")

    st.subheader("Blocked work")
    st.write(
        [
            "real bridge HTTP client",
            "network transport implementation",
            "bridge POST",
            "network sockets",
            "execution implementation",
            "implementation phase start",
            "operator signoff or approval creation",
            "final approval or design closure record creation",
            "platform database mutation",
            "bridge mutation",
            "live LACRM write",
        ]
    )


if __name__ == "__main__":
    render()
