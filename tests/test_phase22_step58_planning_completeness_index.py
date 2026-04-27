from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/phase22_step58_planning_completeness_index.ps1"
PAGE = ROOT / "ui/pages/164_Phase22_Step58_Planning_Completeness_Index.py"
DOC = ROOT / "docs/PHASE22_STEP58_PLANNING_COMPLETENESS_INDEX_PACKET.md"
TEST_FILE = ROOT / "tests/test_phase22_step58_planning_completeness_index.py"

STEP_FILES = [SCRIPT, PAGE, DOC, TEST_FILE]


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def public_text() -> str:
    return "\n".join(read(path) for path in [SCRIPT, PAGE, DOC])


def test_step58_files_exist():
    for path in STEP_FILES:
        assert path.exists(), path


def test_step58_paths_are_short_enough_for_windows():
    for path in STEP_FILES:
        assert len(str(path)) < 260


def test_step58_uses_short_branch_name():
    text = read(SCRIPT)
    assert "phase22-step58-planning-completeness-index" in text
    assert "phase22-step58-phase20-network-transport-planning" not in text


def test_step58_script_declares_phase_and_step():
    text = read(SCRIPT)
    assert "Phase 22 Step 58" in text
    assert "Phase 20 Network Transport Planning Completeness Index Packet" in text


def test_step58_step_files_are_declared():
    text = read(SCRIPT)
    for rel in ['scripts/phase22_step58_planning_completeness_index.ps1', 'ui/pages/164_Phase22_Step58_Planning_Completeness_Index.py', 'docs/PHASE22_STEP58_PLANNING_COMPLETENESS_INDEX_PACKET.md', 'tests/test_phase22_step58_planning_completeness_index.py']:
        assert rel in text


def test_step58_page_number_is_correct():
    assert "ui/pages/164_Phase22_Step58_Planning_Completeness_Index.py" in PAGE.as_posix()


def test_step58_page_title_is_correct():
    text = read(PAGE)
    assert "Phase 22 Step 58" in text
    assert "Planning Completeness Index" in text


def test_step58_doc_title_is_correct():
    assert "# Phase 22 Step 58 - Phase 20 Network Transport Planning Completeness Index Packet" in read(DOC)


def test_step58_doc_lists_all_step_files():
    text = read(DOC)
    for rel in ['scripts/phase22_step58_planning_completeness_index.ps1', 'ui/pages/164_Phase22_Step58_Planning_Completeness_Index.py', 'docs/PHASE22_STEP58_PLANNING_COMPLETENESS_INDEX_PACKET.md', 'tests/test_phase22_step58_planning_completeness_index.py']:
        assert rel in text


def test_step58_planning_only_is_declared():
    text = public_text()
    assert "planning_only" in text
    assert "Planning-only" in text or "planning-only" in text


def test_step58_no_platform_db_mutation_guard_exists():
    assert "no_platform_db_mutation" in public_text()


def test_step58_no_bridge_mutation_guard_exists():
    assert "no_bridge_mutation" in public_text()


def test_step58_no_real_bridge_http_client_guard_exists():
    assert "no_real_bridge_http_client" in public_text()


def test_step58_no_network_transport_guard_exists():
    assert "no_network_transport_implementation" in public_text()


def test_step58_no_bridge_post_guard_exists():
    assert "no_bridge_post" in public_text()


def test_step58_no_network_sockets_guard_exists():
    assert "no_network_sockets" in public_text()


def test_step58_lacrm_dry_run_guard_exists():
    text = public_text()
    assert "lacrm_default_mode" in text
    assert "dry_run" in text


def test_step58_live_write_guards_exist():
    text = public_text()
    assert "live_write_disabled" in text
    assert "live_write_unarmed" in text


def test_step58_completeness_index_guards_exist():
    text = public_text()
    assert "planning_completeness_index_record_creation" in text
    assert "planning_completeness_index_approval_creation" in text
    assert "implementation_prerequisite_queue_creation" in text
    assert "phase22_closeout_creation" in text
    assert "phase23_start_boundary_creation" in text


def test_step58_completeness_index_items_exist():
    text = public_text()
    for marker in [
        "connector_first_operating_core",
        "source_bucket_flow",
        "canonical_event_ledger",
        "expected_actual_variance",
        "driver_attribution",
        "probabilistic_calibration",
        "pattern_detection",
        "recommendation_engine_boundary",
        "decision_boundary_governance",
        "human_review_gate",
        "approval_audit_trail",
        "rollback_recovery",
        "deployment_readiness",
        "exit_readiness",
        "handoff_dossier",
        "closure_deferral_resolution_chain",
    ]:
        assert marker in text


def test_step58_does_not_assign_unsafe_creation_true_in_public_files():
    text = public_text()
    forbidden_patterns = [
        r"(?m)^\s*implementation_phase_start\s*=\s*\$true\b",
        r"(?m)^\s*authorization_record_creation\s*=\s*\$true\b",
        r"(?m)^\s*operator_signoff_creation\s*=\s*\$true\b",
        r"(?m)^\s*operator_approval_creation\s*=\s*\$true\b",
        r"(?m)^\s*final_approval_creation\s*=\s*\$true\b",
        r"(?m)^\s*design_closure_record_creation\s*=\s*\$true\b",
        r"(?m)^\s*planning_completeness_index_record_creation\s*=\s*\$true\b",
        r"(?m)^\s*planning_completeness_index_approval_creation\s*=\s*\$true\b",
        r"(?m)^\s*implementation_prerequisite_queue_creation\s*=\s*\$true\b",
        r"(?m)^\s*phase22_closeout_creation\s*=\s*\$true\b",
        r"(?m)^\s*phase23_start_boundary_creation\s*=\s*\$true\b",
    ]
    for pattern in forbidden_patterns:
        assert not re.search(pattern, text)


def test_step58_packet_generation_is_json_only():
    text = read(SCRIPT)
    assert "ConvertTo-Json" in text
    assert "phase22_step58_planning_completeness_index_packet.json" in text


def test_step58_expected_smoke_text_exists():
    assert "SMOKE TEST PASS: Phase 22 Step 58 Phase 20 Network Transport Planning Completeness Index Packet is present and planning-only." in read(SCRIPT)


def test_step58_server_start_placeholder_exists():
    text = read(SCRIPT)
    assert "Server startup is intentionally disabled" in text
    assert "network socket" in text


def test_step58_no_double_dash_text_in_public_docs():
    for path in [PAGE, DOC]:
        assert "--" not in read(path)


def test_step58_test_count_anchor():
    test_functions = [line for line in read(TEST_FILE).splitlines() if line.startswith("def test_")]
    assert len(test_functions) == 26

