from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts/phase26_step58_implementation_transition_no_write_dry_run_result_review_planning_operator_hold_point_packet.ps1"
PAGE = REPO_ROOT / "ui/pages/554_Phase26_Step58_Implementation_Transition_NoWrite_Dry_Run_Result_Review_Planning_Operator_Hold_Point_Packet.py"
DOC = REPO_ROOT / "docs/PHASE26_STEP58_IMPLEMENTATION_TRANSITION_NO_WRITE_DRY_RUN_RESULT_REVIEW_PLANNING_OPERATOR_HOLD_POINT_PACKET.md"
TEST = REPO_ROOT / "tests/test_phase26_step58_implementation_transition_no_write_dry_run_result_review_planning_operator_hold_point_packet.py"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def compact(text: str) -> str:
    return "".join(text.lower().split())


def operational_text() -> str:
    return compact("\n".join(read(path) for path in (SCRIPT, PAGE, DOC)))


def test_phase26_step58_files_are_present():
    for path in (SCRIPT, PAGE, DOC, TEST):
        assert path.exists(), f"missing {path}"


def test_phase26_step58_launcher_markers_are_present():
    text = read(SCRIPT).lower()
    assert "phase 26 step 58" in text
    assert "phase26-step58-implementation-transition-no-write-dry-run-result-review-planning-operator-hold-point" in text
    assert "planning_only" in text
    assert "no_network_transport_implementation" in text
    assert "phase27_start" in text
    assert "phase27_boundary_creation" in text
    assert "batch_risk_review_location" in text


def test_phase26_step58_planning_only_safety_markers():
    text = operational_text()
    required = [
        "planning_only",
        "no_real_bridge_http_client",
        "no_network_transport_implementation",
        "no_bridge_post",
        "no_network_sockets",
        "phase26_execution_start",
        "phase26_implementation_start",
        "implementation_phase_start",
        "post_closeout_runtime_start",
        "transition_runtime_start",
        "transition_execution_start",
        "network_transport_runtime_start",
        "phase27_start",
        "phase27_boundary_creation",
        "implementation_transition_runtime_creation",
        "implementation_transition_execution",
        "live_write_disabled",
        "live_write_unarmed",
    ]
    for marker in required:
        assert marker in text


def test_phase26_step58_does_not_start_runtime_or_next_phase():
    text = operational_text()
    forbidden = [
        "phase27_start=true",
        "phase27_boundary_creation=true",
        "phase26_execution_start=true",
        "phase26_implementation_start=true",
        "implementation_phase_start=true",
        "post_closeout_runtime_start=true",
        "controlled_activation_runtime_start=true",
        "network_transport_runtime_start=true",
        "bridge_transport_runtime_start=true",
        "transition_runtime_start=true",
        "transition_execution_start=true",
        "implementation_transition_runtime_creation=true",
        "implementation_transition_execution=true",
        "implementation_transition_decision_creation=true",
        "implementation_transition_approval_creation=true",
        "implementation_transition_operator_approval_creation=true",
        "release_gate_runtime_start=true",
        "no_network_sockets=false",
        "no_bridge_post=false",
        "live_write_disabled=false",
        "live_write_unarmed=false",
    ]
    for marker in forbidden:
        assert marker not in text


def test_phase26_step58_batch_risk_review_is_chat_only_not_powershell_prompt():
    text = operational_text()
    assert "batch_risk_review_location" in text
    assert "chat_only" in text
    assert "lower_batch_size_required=true" not in text
    script_text = read(SCRIPT)
    assert "Read-Host" not in script_text
    assert "COMPLEXITY GATE" not in script_text


def test_phase26_step58_launcher_supports_optimized_actions_and_known_fixes():
    script = read(SCRIPT)
    assert "ValidateSet(\"status\", \"apply\", \"smoke\", \"packet\", \"all\")" in script
    assert "APPLY PASS: Phase 26 Step 58" in script
    assert "SMOKE TEST PASS: Phase 26 Step 58" in script
    assert "CHECK: packet_json=" in script
    assert "$File:" not in script
    assert "Join-Path $RepoRoot \"scripts/phase26_step58_implementation_transition_no_write_dry_run_result_review_planning_operator_hold_point_packet.ps1\"," not in script
    assert "System.Object[]" not in script


def test_phase26_step58_docs_are_operator_readable():
    text = read(DOC)
    assert "Phase 26 Step 58 - Phase 20 Network Transport Implementation Transition No-Write Dry Run Result Review Planning Operator Hold Point Packet" in text
    assert "Expected option 3 smoke text" in text
    assert "Expected option 5 / packet output includes" in text
    assert "No server launch" in text


def test_phase26_step58_ui_is_streamlit_reference_only_page():
    text = read(PAGE).lower()
    assert "import streamlit as st" in text
    assert "reference-only" in text or "planning-only" in text
    assert "phase27_start=false" in text


def test_phase26_step58_test_file_self_identifies_step():
    text = read(TEST).lower()
    assert "step58" in text or "step 58" in text
