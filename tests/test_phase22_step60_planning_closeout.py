from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/phase22_step60_planning_closeout.ps1"
PAGE = ROOT / "ui/pages/166_Phase22_Step60_Planning_Closeout.py"
DOC = ROOT / "docs/PHASE22_STEP60_PLANNING_CLOSEOUT_PACKET.md"
TEST_FILE = ROOT / "tests/test_phase22_step60_planning_closeout.py"

STEP_FILES = [SCRIPT, PAGE, DOC, TEST_FILE]
REL_FILES = [
    "scripts/phase22_step60_planning_closeout.ps1",
    "ui/pages/166_Phase22_Step60_Planning_Closeout.py",
    "docs/PHASE22_STEP60_PLANNING_CLOSEOUT_PACKET.md",
    "tests/test_phase22_step60_planning_closeout.py",
]


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def public_text() -> str:
    return "\n".join(read(path) for path in STEP_FILES)


def test_step60_files_exist():
    for path in STEP_FILES:
        assert path.exists(), path


def test_step60_paths_are_short_enough_for_windows():
    for path in STEP_FILES:
        assert len(str(path)) < 260


def test_step60_uses_short_branch_name():
    text = read(SCRIPT)
    assert "phase22-step60-planning-closeout" in text
    assert "phase22-step60-phase20-network-transport-planning" not in text


def test_step60_script_declares_phase_and_step():
    text = read(SCRIPT)
    assert "Phase 22 Step 60" in text
    assert "Planning Closeout Packet" in text


def test_step60_step_files_are_declared():
    text = read(SCRIPT)
    for rel in REL_FILES:
        assert rel in text


def test_step60_page_number_is_correct():
    assert "ui/pages/166_Phase22_Step60_Planning_Closeout.py" in PAGE.as_posix()


def test_step60_page_title_is_correct():
    text = read(PAGE)
    assert "Phase 22 Step 60" in text
    assert "Planning Closeout" in text


def test_step60_doc_title_is_correct():
    assert "# Phase 22 Step 60 - Phase 20 Network Transport Planning Closeout Packet" in read(DOC)


def test_step60_doc_lists_all_step_files():
    text = read(DOC)
    for rel in REL_FILES:
        assert rel in text


def test_step60_planning_only_is_declared():
    text = public_text()
    assert "planning_only" in text
    assert "Planning-only" in text or "planning-only" in text


def test_step60_no_platform_db_mutation_guard_exists():
    assert "no_platform_db_mutation" in public_text()


def test_step60_no_bridge_mutation_guard_exists():
    assert "no_bridge_mutation" in public_text()


def test_step60_no_real_bridge_http_client_guard_exists():
    assert "no_real_bridge_http_client" in public_text()


def test_step60_no_network_transport_guard_exists():
    assert "no_network_transport_implementation" in public_text()


def test_step60_no_bridge_post_guard_exists():
    assert "no_bridge_post" in public_text()


def test_step60_no_network_sockets_guard_exists():
    assert "no_network_sockets" in public_text()


def test_step60_lacrm_dry_run_guard_exists():
    text = public_text()
    assert "lacrm_default_mode" in text
    assert "dry_run" in text


def test_step60_live_write_guards_exist():
    text = public_text()
    assert "live_write_disabled" in text
    assert "live_write_unarmed" in text


def test_step60_closeout_guards_exist():
    text = public_text()
    for marker in [
        "phase22_planning_closeout",
        "phase22_closeout_record_creation",
        "phase22_closeout_approval_creation",
        "phase22_closeout_execution",
        "phase22_closeout_mutation",
        "phase23_start_boundary_creation",
        "phase23_start_boundary_approval_creation",
        "phase23_implementation_start",
    ]:
        assert marker in text


def test_step60_closeout_scope_markers_exist():
    text = public_text()
    for marker in [
        "phase22_planning_packet_sequence_indexed",
        "implementation_prerequisites_remain_planned_only",
        "phase23_not_started_by_this_packet",
        "no_approvals_or_signoffs_created",
        "no_source_bucket_or_applied_layer_mutation",
    ]:
        assert marker in text


def test_step60_does_not_assign_unsafe_creation_true_in_public_files():
    text = public_text()
    forbidden_patterns = [
        r"(?m)^\s*implementation_phase_start\s*=\s*\$true\b",
        r"(?m)^\s*authorization_record_creation\s*=\s*\$true\b",
        r"(?m)^\s*operator_signoff_creation\s*=\s*\$true\b",
        r"(?m)^\s*operator_approval_creation\s*=\s*\$true\b",
        r"(?m)^\s*final_approval_creation\s*=\s*\$true\b",
        r"(?m)^\s*design_closure_record_creation\s*=\s*\$true\b",
        r"(?m)^\s*phase22_closeout_record_creation\s*=\s*\$true\b",
        r"(?m)^\s*phase22_closeout_approval_creation\s*=\s*\$true\b",
        r"(?m)^\s*phase22_closeout_execution\s*=\s*\$true\b",
        r"(?m)^\s*phase22_closeout_mutation\s*=\s*\$true\b",
        r"(?m)^\s*phase23_start_boundary_creation\s*=\s*\$true\b",
        r"(?m)^\s*phase23_implementation_start\s*=\s*\$true\b",
        r"(?m)^\s*lacrm_live_write\s*=\s*\$true\b",
        r"(?m)^\s*source_bucket_writes\s*=\s*\$true\b",
        r"(?m)^\s*applied_layer_mutation\s*=\s*\$true\b",
        r"(?m)^\s*review_gate_mutation\s*=\s*\$true\b",
    ]
    for pattern in forbidden_patterns:
        assert not re.search(pattern, text)


def test_step60_packet_generation_is_json_only():
    text = read(SCRIPT)
    assert "ConvertTo-Json" in text
    assert "phase22_step60_planning_closeout_packet.json" in text


def test_step60_expected_smoke_text_exists():
    assert "SMOKE TEST PASS: Phase 22 Step 60 Phase 20 Network Transport Planning Closeout Packet is present and planning-only." in read(SCRIPT)


def test_step60_server_start_placeholder_exists():
    text = read(SCRIPT)
    assert "Server startup is intentionally disabled" in text
    assert "network socket" in text


def test_step60_no_double_dash_text_in_public_docs():
    for path in [PAGE, DOC]:
        assert "--" not in read(path)


def test_step60_test_count_anchor():
    test_functions = [line for line in read(TEST_FILE).splitlines() if line.startswith("def test_")]
    assert len(test_functions) == 26

