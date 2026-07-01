from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts/phase25_step100_post_closeout_final_release_hold_planning_final_boundary_confirmation_packet.ps1"
UI = REPO / "ui/pages/476_Phase25_Step100_Implementation_PostCloseout_Final_Release_Hold_Planning_Final_Boundary_Confirmation_Packet.py"
DOC = REPO / "docs/PHASE25_STEP100_POST_CLOSEOUT_FINAL_RELEASE_HOLD_PLANNING_FINAL_BOUNDARY_CONFIRMATION_PACKET.md"
TEST = REPO / "tests/test_phase25_step100_post_closeout_final_release_hold_planning_final_boundary_confirmation_packet.py"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def compact(text: str) -> str:
    return "".join(text.lower().split())


def test_phase25_step100_files_exist():
    assert SCRIPT.exists()
    assert UI.exists()
    assert DOC.exists()
    assert TEST.exists()


def test_phase25_step100_launcher_markers():
    text = read(SCRIPT).lower()
    assert "phase 25 step 100" in text
    assert "phase25-step100-post-closeout-final-release-hold-planning-final-boundary-confirmation" in text
    assert "planning_only" in text
    assert "no_network_transport_implementation" in text
    assert "phase26_start" in text
    assert "phase26_boundary_creation" in text
    assert "complexity_batch_gate" in text


def test_phase25_step100_planning_only_safety_markers():
    text = compact(read(SCRIPT) + read(DOC) + read(UI))
    required = [
        "planning_only",
        "no_real_bridge_http_client",
        "no_network_transport_implementation",
        "no_bridge_post",
        "no_network_sockets",
        "phase25_execution_start",
        "phase25_implementation_start",
        "implementation_phase_start",
        "post_closeout_runtime_start",
        "phase26_start",
        "phase26_boundary_creation",
        "final_release_hold_record_creation",
        "final_release_hold_decision_creation",
        "final_release_hold_approval_creation",
        "final_release_execution",
        "live_write_disabled",
        "live_write_unarmed",
    ]
    for marker in required:
        assert marker in text


def test_phase25_step100_does_not_start_runtime_or_next_phase():
    operational = compact(read(SCRIPT) + read(DOC) + read(UI))
    forbidden = [
        "phase26_start=true",
        "phase26_boundary_creation=true",
        "phase25_execution_start=true",
        "phase25_implementation_start=true",
        "implementation_phase_start=true",
        "post_closeout_runtime_start=true",
        "controlled_activation_runtime_start=true",
        "network_transport_runtime_start=true",
        "bridge_transport_runtime_start=true",
        "final_release_hold_record_creation=true",
        "final_release_hold_decision_creation=true",
        "final_release_hold_approval_creation=true",
        "final_release_execution=true",
        "no_network_sockets=false",
        "no_bridge_post=false",
        "live_write_disabled=false",
        "live_write_unarmed=false",
    ]
    for marker in forbidden:
        assert marker not in operational


def test_phase25_step100_complexity_gate_allows_standard_planning_only_batch():
    text = compact(read(SCRIPT) + read(DOC) + read(UI))
    assert "complexity_batch_gate" in text
    assert "standard_planning_only_with_release_hold_language" in text
    assert "complexity_review_required" in text
    assert "lower_batch_size_required" in text
    assert "lower_batch_size_required=true" not in text
    assert "complexity_review_required=true" not in text


def test_phase25_step100_docs_are_operator_readable():
    text = read(DOC)
    assert "Phase 25 Step 100 - Phase 20 Network Transport Implementation Post-Closeout Final Release Hold Planning Final Boundary Confirmation Packet" in text
    assert "Expected option 3 smoke text" in text
    assert "Expected option 5 / packet output includes" in text
    assert "No server launch" in text


def test_phase25_step100_ui_is_streamlit_reference_only_page():
    text = read(UI)
    assert "import streamlit as st" in text
    assert "reference-only" in text.lower() or "planning-only" in text.lower()
    assert "phase26_start=false" in text


def test_phase25_step100_test_file_self_identifies_step():
    text = read(TEST).lower()
    assert "step100" in text or "step 100" in text
