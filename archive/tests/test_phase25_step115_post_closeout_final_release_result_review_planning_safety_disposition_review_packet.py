from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts/phase25_step115_post_closeout_final_release_result_review_planning_safety_disposition_review_packet.ps1"
PAGE = REPO_ROOT / "ui/pages/491_Phase25_Step115_Implementation_PostCloseout_Final_Release_Result_Review_Planning_Safety_Disposition_Review_Packet.py"
DOC = REPO_ROOT / "docs/PHASE25_STEP115_POST_CLOSEOUT_FINAL_RELEASE_RESULT_REVIEW_PLANNING_SAFETY_DISPOSITION_REVIEW_PACKET.md"
TEST = REPO_ROOT / "tests/test_phase25_step115_post_closeout_final_release_result_review_planning_safety_disposition_review_packet.py"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def compact(text: str) -> str:
    return "".join(text.lower().split())


def operational_text() -> str:
    return compact("\n".join(read(path) for path in (SCRIPT, PAGE, DOC)))


def test_phase25_step115_files_are_present():
    for path in (SCRIPT, PAGE, DOC, TEST):
        assert path.exists(), f"missing {path}"


def test_phase25_step115_launcher_markers_are_present():
    text = read(SCRIPT).lower()
    assert "phase 25 step 115" in text
    assert "phase25-step115-post-closeout-final-release-result-review-planning-safety-disposition-review" in text
    assert "planning_only" in text
    assert "no_network_transport_implementation" in text
    assert "phase26_start" in text
    assert "phase26_boundary_creation" in text
    assert "batch_risk_review_location" in text


def test_phase25_step115_planning_only_safety_markers():
    text = operational_text()
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
        "final_release_result_review_record_creation",
        "final_release_result_review_decision_creation",
        "final_release_result_review_approval_creation",
        "phase25_closeout_hold_record_creation",
        "phase25_closeout_hold_approval_creation",
        "phase25_closeout_hold_execution",
        "final_release_execution",
        "release_gate_runtime_start",
        "live_write_disabled",
        "live_write_unarmed",
    ]
    for marker in required:
        assert marker in text


def test_phase25_step115_does_not_start_runtime_or_next_phase():
    text = operational_text()
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
        "final_release_result_review_record_creation=true",
        "final_release_result_review_decision_creation=true",
        "final_release_result_review_approval_creation=true",
        "phase25_closeout_hold_record_creation=true",
        "phase25_closeout_hold_approval_creation=true",
        "phase25_closeout_hold_execution=true",
        "final_release_execution=true",
        "release_gate_runtime_start=true",
        "no_network_sockets=false",
        "no_bridge_post=false",
        "live_write_disabled=false",
        "live_write_unarmed=false",
    ]
    for marker in forbidden:
        assert marker not in text


def test_phase25_step115_batch_risk_review_is_chat_only_not_powershell_prompt():
    text = operational_text()
    assert "batch_risk_review_location" in text
    assert "chat_only" in text
    assert "lower_batch_size_required=true" not in text
    script_text = read(SCRIPT)
    assert "Read-Host" not in script_text
    assert "COMPLEXITY GATE" not in script_text


def test_phase25_step115_launcher_supports_optimized_actions_and_known_fixes():
    script = read(SCRIPT)
    assert "ValidateSet(\"status\", \"apply\", \"smoke\", \"packet\", \"all\")" in script
    assert "APPLY PASS: Phase 25 Step 115" in script
    assert "SMOKE TEST PASS: Phase 25 Step 115" in script
    assert "CHECK: packet_json=" in script
    assert "$File:" not in script
    assert "Join-Path $RepoRoot \"scripts/phase25_step115_post_closeout_final_release_result_review_planning_safety_disposition_review_packet.ps1\"," not in script
    assert "System.Object[]" not in script


def test_phase25_step115_docs_are_operator_readable():
    text = read(DOC)
    assert "Phase 25 Step 115 - Phase 20 Network Transport Implementation Post-Closeout Final Release Result Review Planning Safety Disposition Review Packet" in text
    assert "Expected option 3 smoke text" in text
    assert "Expected option 5 / packet output includes" in text
    assert "No server launch" in text


def test_phase25_step115_ui_is_streamlit_reference_only_page():
    text = read(PAGE).lower()
    assert "import streamlit as st" in text
    assert "reference-only" in text or "planning-only" in text
    assert "phase26_start=false" in text


def test_phase25_step115_test_file_self_identifies_step():
    text = read(TEST).lower()
    assert "step115" in text or "step 115" in text
