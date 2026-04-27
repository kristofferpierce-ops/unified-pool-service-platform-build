from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/phase22_step59_implementation_prereq_backlog.ps1"
PAGE = ROOT / "ui/pages/165_Phase22_Step59_Implementation_Prereq_Backlog.py"
DOC = ROOT / "docs/PHASE22_STEP59_IMPLEMENTATION_PREREQ_BACKLOG_PACKET.md"
TEST_FILE = ROOT / "tests/test_phase22_step59_implementation_prereq_backlog.py"

STEP_FILES = [SCRIPT, PAGE, DOC, TEST_FILE]


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def public_text() -> str:
    return "\n".join(read(path) for path in STEP_FILES)


def test_step59_files_exist():
    for path in STEP_FILES:
        assert path.exists(), path


def test_step59_paths_are_short_enough_for_windows():
    for path in STEP_FILES:
        assert len(str(path)) < 260


def test_step59_uses_short_branch_name():
    text = read(SCRIPT)
    assert "phase22-step59-implementation-prereq-backlog" in text
    assert "phase22-step59-phase20-network-transport-planning" not in text


def test_step59_script_declares_phase_and_step():
    text = read(SCRIPT)
    assert "Phase 22 Step 59" in text
    assert "Implementation Prerequisite Backlog Packet" in text


def test_step59_step_files_are_declared():
    text = read(SCRIPT)
    for rel in ['scripts/phase22_step59_implementation_prereq_backlog.ps1', 'ui/pages/165_Phase22_Step59_Implementation_Prereq_Backlog.py', 'docs/PHASE22_STEP59_IMPLEMENTATION_PREREQ_BACKLOG_PACKET.md', 'tests/test_phase22_step59_implementation_prereq_backlog.py']:
        assert rel in text


def test_step59_page_number_is_correct():
    assert "ui/pages/165_Phase22_Step59_Implementation_Prereq_Backlog.py" in PAGE.as_posix()


def test_step59_page_title_is_correct():
    text = read(PAGE)
    assert "Phase 22 Step 59" in text
    assert "Implementation Prerequisite Backlog" in text


def test_step59_doc_title_is_correct():
    assert "# Phase 22 Step 59 - Phase 20 Network Transport Planning Implementation Prerequisite Backlog Packet" in read(DOC)


def test_step59_doc_lists_all_step_files():
    text = read(DOC)
    for rel in ['scripts/phase22_step59_implementation_prereq_backlog.ps1', 'ui/pages/165_Phase22_Step59_Implementation_Prereq_Backlog.py', 'docs/PHASE22_STEP59_IMPLEMENTATION_PREREQ_BACKLOG_PACKET.md', 'tests/test_phase22_step59_implementation_prereq_backlog.py']:
        assert rel in text


def test_step59_planning_only_is_declared():
    text = public_text()
    assert "planning_only" in text
    assert "Planning-only" in text or "planning-only" in text


def test_step59_no_platform_db_mutation_guard_exists():
    assert "no_platform_db_mutation" in public_text()


def test_step59_no_bridge_mutation_guard_exists():
    assert "no_bridge_mutation" in public_text()


def test_step59_no_real_bridge_http_client_guard_exists():
    assert "no_real_bridge_http_client" in public_text()


def test_step59_no_network_transport_guard_exists():
    assert "no_network_transport_implementation" in public_text()


def test_step59_no_bridge_post_guard_exists():
    assert "no_bridge_post" in public_text()


def test_step59_no_network_sockets_guard_exists():
    assert "no_network_sockets" in public_text()


def test_step59_lacrm_dry_run_guard_exists():
    text = public_text()
    assert "lacrm_default_mode" in text
    assert "dry_run" in text


def test_step59_live_write_guards_exist():
    text = public_text()
    assert "live_write_disabled" in text
    assert "live_write_unarmed" in text


def test_step59_implementation_prerequisite_backlog_guards_exist():
    text = public_text()
    for marker in [
        "implementation_prerequisite_backlog",
        "implementation_prerequisite_backlog_record_creation",
        "implementation_prerequisite_backlog_queue_creation",
        "implementation_prerequisite_backlog_approval_creation",
        "implementation_prerequisite_backlog_mutation",
        "implementation_prerequisite_execution",
        "implementation_ready_transition",
        "phase22_closeout_creation",
        "phase23_start_boundary_creation",
    ]:
        assert marker in text


def test_step59_prerequisite_categories_exist():
    text = public_text()
    for marker in [
        "connector_first_operating_core_readiness",
        "source_bucket_flow_readiness",
        "bridge_stabilization_readiness",
        "canonical_event_ledger_readiness",
        "expected_actual_variance_readiness",
        "driver_attribution_readiness",
        "probabilistic_calibration_readiness",
        "pattern_detection_readiness",
        "recommendation_boundary_readiness",
        "decision_governance_readiness",
        "human_review_gate_readiness",
        "approval_audit_trail_readiness",
        "rollback_recovery_readiness",
        "closeout_and_phase_boundary_readiness",
    ]:
        assert marker in text


def test_step59_does_not_assign_unsafe_creation_true_in_public_files():
    text = public_text()
    forbidden_patterns = [
        r"(?m)^\s*implementation_phase_start\s*=\s*\$true\b",
        r"(?m)^\s*authorization_record_creation\s*=\s*\$true\b",
        r"(?m)^\s*operator_signoff_creation\s*=\s*\$true\b",
        r"(?m)^\s*operator_approval_creation\s*=\s*\$true\b",
        r"(?m)^\s*final_approval_creation\s*=\s*\$true\b",
        r"(?m)^\s*design_closure_record_creation\s*=\s*\$true\b",
        r"(?m)^\s*implementation_prerequisite_backlog_record_creation\s*=\s*\$true\b",
        r"(?m)^\s*implementation_prerequisite_backlog_queue_creation\s*=\s*\$true\b",
        r"(?m)^\s*implementation_prerequisite_backlog_approval_creation\s*=\s*\$true\b",
        r"(?m)^\s*implementation_prerequisite_backlog_mutation\s*=\s*\$true\b",
        r"(?m)^\s*implementation_prerequisite_execution\s*=\s*\$true\b",
        r"(?m)^\s*implementation_ready_transition\s*=\s*\$true\b",
        r"(?m)^\s*phase22_closeout_creation\s*=\s*\$true\b",
        r"(?m)^\s*phase23_start_boundary_creation\s*=\s*\$true\b",
    ]
    for pattern in forbidden_patterns:
        assert not re.search(pattern, text)


def test_step59_packet_generation_is_json_only():
    text = read(SCRIPT)
    assert "ConvertTo-Json" in text
    assert "phase22_step59_implementation_prereq_backlog_packet.json" in text


def test_step59_expected_smoke_text_exists():
    assert "SMOKE TEST PASS: Phase 22 Step 59 Phase 20 Network Transport Planning Implementation Prerequisite Backlog Packet is present and planning-only." in read(SCRIPT)


def test_step59_server_start_placeholder_exists():
    text = read(SCRIPT)
    assert "Server startup is intentionally disabled" in text
    assert "network socket" in text


def test_step59_no_double_dash_text_in_public_docs():
    for path in [PAGE, DOC]:
        assert "--" not in read(path)


def test_step59_test_count_anchor():
    test_functions = [line for line in read(TEST_FILE).splitlines() if line.startswith("def test_")]
    assert len(test_functions) == 26

