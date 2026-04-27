from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]

SCRIPT_REL = "scripts/phase22_generate_cross_repo_handoff_packet.ps1"
PAGE_REL = "ui/pages/167_Phase20_Network_Transport_Planning_Cross_Repo_Handoff_Packet.py"
DOC_REL = "docs/PHASE22_STEP61_CROSS_REPO_HANDOFF_PACKET.md"
TEST_REL = "tests/test_phase22_step61_cross_repo_handoff_packet.py"

SCRIPT = ROOT / SCRIPT_REL
PAGE = ROOT / PAGE_REL
DOC = ROOT / DOC_REL
TEST_FILE = ROOT / TEST_REL

PUBLIC_FILES = [SCRIPT, PAGE, DOC, TEST_FILE]
PUBLIC_RUNTIME_FILES = [SCRIPT, PAGE, DOC]


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def combined_public_text() -> str:
    return "\n".join(read(path) for path in PUBLIC_FILES)


def combined_runtime_text() -> str:
    return "\n".join(read(path) for path in PUBLIC_RUNTIME_FILES)


def test_step61_files_exist():
    for path in PUBLIC_FILES:
        assert path.exists(), path


def test_step61_script_mentions_phase_and_step():
    text = read(SCRIPT)
    assert "Phase 22 Step 61" in text
    assert "Cross-Repo Handoff Packet" in text


def test_step61_page_number_is_correct():
    assert PAGE.as_posix().endswith("ui/pages/167_Phase20_Network_Transport_Planning_Cross_Repo_Handoff_Packet.py")


def test_step61_doc_title_is_correct():
    text = read(DOC)
    assert "# Phase 22 Step 61 - Phase 20 Network Transport Planning Cross-Repo Handoff Packet" in text


def test_step61_launcher_supports_action_all():
    text = read(SCRIPT)
    assert '[ValidateSet("menu", "status", "apply", "smoke", "packet", "all")]' in text
    assert '"all"' in text
    assert "Show-Status" in text
    assert "Apply-StepFiles" in text
    assert "Test-Smoke" in text
    assert "New-Packet" in text


def test_step61_is_planning_only():
    text = combined_public_text()
    required = [
        "planning_only",
        "no_platform_db_mutation",
        "no_bridge_mutation",
        "no_real_bridge_http_client",
        "no_network_transport_implementation",
        "no_bridge_post",
        "no_network_sockets",
        "no_execution_implementation",
        "live_write_disabled",
        "live_write_unarmed",
    ]
    for marker in required:
        assert marker in text


def test_step61_disables_cross_repo_mutation():
    text = combined_public_text()
    required = [
        "cross_repo_write",
        "cross_repo_mutation",
        "external_repo_push",
        "phase23_start",
        "phase23_branch_creation",
        "implementation_queue_creation",
    ]
    for marker in required:
        assert marker in text


def test_step61_keeps_lacrm_dry_run():
    text = combined_public_text()
    assert "dry_run" in text
    assert "lacrm_live_write" in text
    assert "live_write_disabled" in text
    assert "live_write_unarmed" in text


def test_step61_contains_rollout_alignment():
    text = combined_public_text()
    markers = [
        "connector-first",
        "raw",
        "normalized",
        "matched",
        "approved",
        "applied",
        "bridge",
        "connector-package",
    ]
    lowered = text.lower()
    for marker in markers:
        assert marker in lowered


def test_step61_does_not_create_phase23_or_implementation():
    text = combined_runtime_text().lower()
    forbidden = [
        "phase23_start: true",
        "phase23_start = true",
        "phase23_branch_creation: true",
        "phase23_branch_creation = true",
        "implementation_phase_start: true",
        "implementation_phase_start = true",
        "implementation_queue_creation: true",
        "implementation_queue_creation = true",
    ]
    for marker in forbidden:
        assert marker not in text


def test_step61_does_not_enable_network_or_bridge_runtime():
    text = combined_runtime_text().lower()
    forbidden = [
        "no_real_bridge_http_client: false",
        "no_network_transport_implementation: false",
        "no_bridge_post: false",
        "no_network_sockets: false",
        "no_execution_implementation: false",
    ]
    for marker in forbidden:
        assert marker not in text


def test_step61_does_not_write_to_external_repos():
    text = combined_runtime_text().lower()
    forbidden = [
        "cross_repo_write: true",
        "cross_repo_write = true",
        "cross_repo_mutation: true",
        "cross_repo_mutation = true",
        "external_repo_push: true",
        "external_repo_push = true",
    ]
    for marker in forbidden:
        assert marker not in text


def test_step61_does_not_create_approvals_or_closure_records():
    text = combined_runtime_text().lower()
    forbidden = [
        "operator_signoff_creation: true",
        "operator_signoff_creation = true",
        "operator_approval_creation: true",
        "operator_approval_creation = true",
        "final_approval_creation: true",
        "final_approval_creation = true",
        "design_closure_record_creation: true",
        "design_closure_record_creation = true",
    ]
    for marker in forbidden:
        assert marker not in text


def test_step61_menu_has_expected_options():
    text = read(SCRIPT)
    assert "Phase 22 Step 61 menu" in text
    assert "Show status / verify paths" in text
    assert "Smoke test Phase 22 Step 61" in text
    assert "Generate Phase 22 Step 61 cross-repo handoff packet" in text


def test_step61_packet_generates_json_under_backups():
    text = read(SCRIPT)
    assert "backups" in text
    assert "phase22_step61_cross_repo_handoff_packet" in text
    assert "ConvertTo-Json" in text


def test_step61_smoke_success_text_present():
    text = read(SCRIPT)
    expected = (
        "SMOKE TEST PASS: Phase 22 Step 61 Phase 20 Network Transport Planning "
        "Cross-Repo Handoff Packet is present and planning-only."
    )
    assert expected in text


def test_step61_expected_branch_is_short():
    text = read(SCRIPT)
    assert "phase22-step61-cross-repo-handoff" in text
    assert len("phase22-step61-cross-repo-handoff") < 80


def test_step61_test_uses_posix_page_path():
    text = read(TEST_FILE)
    assert "PAGE.as_posix()" in text


def test_step61_installer_paths_are_short():
    for rel in [SCRIPT_REL, PAGE_REL, DOC_REL, TEST_REL]:
        assert len(rel) < 140


def test_step61_no_server_start_claim():
    text = combined_public_text().lower()
    assert "no fastapi" in text or "no fastapi, streamlit" in text
    assert "no database mutation" in text or "no_platform_db_mutation" in text


def test_step61_expected_packet_output_in_doc():
    text = read(DOC)
    assert "PASS: cross_repo_write=false" in text
    assert "PASS: external_repo_push=false" in text
    assert "CHECK: phase23_start=not_started" in text

