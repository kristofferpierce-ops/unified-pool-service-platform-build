from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/phase22_step57_handoff_verification_review_disposition_alignment.ps1"
PAGE = ROOT / "ui/pages/163_Phase22_Step57_Handoff_Verification_Review_Disposition_Alignment.py"
DOC = ROOT / "docs/PHASE22_STEP57_HANDOFF_VERIFICATION_REVIEW_DISPOSITION_ALIGNMENT_PACKET.md"
TEST_FILE = ROOT / "tests/test_phase22_step57_handoff_verification_review_disposition_alignment.py"

STEP_FILES = [SCRIPT, PAGE, DOC, TEST_FILE]


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def public_text() -> str:
    return "\n".join(read(path) for path in [SCRIPT, PAGE, DOC])


def test_step57_files_exist():
    for path in STEP_FILES:
        assert path.exists(), path


def test_step57_paths_are_short_enough_for_windows():
    for path in STEP_FILES:
        assert len(str(path)) < 260


def test_step57_uses_short_branch_name():
    text = read(SCRIPT)
    assert "phase22-step57-verification-review-disposition-alignment" in text
    assert "phase22-step57-phase20-network-transport-planning-closure" not in text


def test_step57_script_declares_phase_and_step():
    text = read(SCRIPT)
    assert "Phase 22 Step 57" in text
    assert "Phase 20 Network Transport Planning Closure Deferral Acceptance Evidence Review Disposition Handoff Verification Review Disposition Alignment Packet" in text


def test_step57_step_files_are_declared():
    text = read(SCRIPT)
    for rel in ['scripts/phase22_step57_handoff_verification_review_disposition_alignment.ps1', 'ui/pages/163_Phase22_Step57_Handoff_Verification_Review_Disposition_Alignment.py', 'docs/PHASE22_STEP57_HANDOFF_VERIFICATION_REVIEW_DISPOSITION_ALIGNMENT_PACKET.md', 'tests/test_phase22_step57_handoff_verification_review_disposition_alignment.py']:
        assert rel in text


def test_step57_page_number_is_correct():
    assert "ui/pages/163_Phase22_Step57_Handoff_Verification_Review_Disposition_Alignment.py" in PAGE.as_posix()


def test_step57_page_title_is_correct():
    text = read(PAGE)
    assert "Phase 22 Step 57" in text
    assert "Handoff Verification Review Disposition Alignment" in text


def test_step57_doc_title_is_correct():
    assert "# Phase 22 Step 57 - Phase 20 Network Transport Planning Closure Deferral Acceptance Evidence Review Disposition Handoff Verification Review Disposition Alignment Packet" in read(DOC)


def test_step57_doc_lists_all_step_files():
    text = read(DOC)
    for rel in ['scripts/phase22_step57_handoff_verification_review_disposition_alignment.ps1', 'ui/pages/163_Phase22_Step57_Handoff_Verification_Review_Disposition_Alignment.py', 'docs/PHASE22_STEP57_HANDOFF_VERIFICATION_REVIEW_DISPOSITION_ALIGNMENT_PACKET.md', 'tests/test_phase22_step57_handoff_verification_review_disposition_alignment.py']:
        assert rel in text


def test_step57_planning_only_is_declared():
    text = public_text()
    assert "planning_only" in text
    assert "Planning-only" in text or "planning-only" in text


def test_step57_no_platform_db_mutation_guard_exists():
    assert "no_platform_db_mutation" in public_text()


def test_step57_no_bridge_mutation_guard_exists():
    assert "no_bridge_mutation" in public_text()


def test_step57_no_real_bridge_http_client_guard_exists():
    assert "no_real_bridge_http_client" in public_text()


def test_step57_no_network_transport_guard_exists():
    assert "no_network_transport_implementation" in public_text()


def test_step57_no_bridge_post_guard_exists():
    assert "no_bridge_post" in public_text()


def test_step57_no_network_sockets_guard_exists():
    assert "no_network_sockets" in public_text()


def test_step57_lacrm_dry_run_guard_exists():
    text = public_text()
    assert "lacrm_default_mode" in text
    assert "dry_run" in text


def test_step57_live_write_guards_exist():
    text = public_text()
    assert "live_write_disabled" in text
    assert "live_write_unarmed" in text


def test_step57_handoff_verification_review_disposition_guards_exist():
    text = public_text()
    assert "handoff_verification_review_disposition_creation" in text
    assert "handoff_verification_review_disposition_approval_creation" in text
    assert "handoff_verification_review_disposition_execution" in text


def test_step57_does_not_assign_unsafe_creation_true_in_public_files():
    text = public_text()
    forbidden_patterns = [
        r"(?m)^\s*implementation_phase_start\s*=\s*\$true\b",
        r"(?m)^\s*authorization_record_creation\s*=\s*\$true\b",
        r"(?m)^\s*operator_signoff_creation\s*=\s*\$true\b",
        r"(?m)^\s*operator_approval_creation\s*=\s*\$true\b",
        r"(?m)^\s*final_approval_creation\s*=\s*\$true\b",
        r"(?m)^\s*design_closure_record_creation\s*=\s*\$true\b",
        r"(?m)^\s*handoff_verification_review_disposition_creation\s*=\s*\$true\b",
        r"(?m)^\s*handoff_verification_review_disposition_approval_creation\s*=\s*\$true\b",
        r"(?m)^\s*handoff_verification_review_disposition_execution\s*=\s*\$true\b",
    ]
    for pattern in forbidden_patterns:
        assert not re.search(pattern, text)


def test_step57_packet_generation_is_json_only():
    text = read(SCRIPT)
    assert "ConvertTo-Json" in text
    assert "phase22_step57_handoff_verification_review_disposition_packet.json" in text


def test_step57_expected_smoke_text_exists():
    assert "SMOKE TEST PASS: Phase 22 Step 57 Phase 20 Network Transport Planning Closure Deferral Acceptance Evidence Review Disposition Handoff Verification Review Disposition Alignment Packet is present and planning-only." in read(SCRIPT)


def test_step57_server_start_placeholder_exists():
    text = read(SCRIPT)
    assert "Server startup is intentionally disabled" in text
    assert "network socket" in text


def test_step57_no_double_dash_text_in_public_docs():
    for path in [PAGE, DOC]:
        assert "--" not in read(path)


def test_step57_test_count_anchor():
    test_functions = [line for line in read(TEST_FILE).splitlines() if line.startswith("def test_")]
    assert len(test_functions) == 25

