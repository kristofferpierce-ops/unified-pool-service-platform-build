from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
STEP = 54
PHASE_STEP = "Phase 22 Step 54"
PACKET_NAME = "Phase 20 Network Transport Planning Closure Deferral Acceptance Evidence Review Disposition Handoff Alignment Packet"

SCRIPT = REPO_ROOT / "scripts/phase22_generate_phase20_network_transport_planning_closure_deferral_acceptance_evidence_review_disposition_handoff_alignment_packet.ps1"
PAGE = REPO_ROOT / "ui/pages/160_Phase20_Network_Transport_Planning_Closure_Deferral_Acceptance_Evidence_Review_Disposition_Handoff_Alignment_Packet.py"
DOC = REPO_ROOT / "docs/PHASE22_STEP54_PHASE20_NETWORK_TRANSPORT_PLANNING_CLOSURE_DEFERRAL_ACCEPTANCE_EVIDENCE_REVIEW_DISPOSITION_HANDOFF_ALIGNMENT_PACKET.md"
TEST_FILE = REPO_ROOT / "tests/test_phase22_phase20_network_transport_planning_closure_deferral_acceptance_evidence_review_disposition_handoff_alignment_packet.py"
STEP_FILES = [SCRIPT, PAGE, DOC, TEST_FILE]


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_step54_files_exist():
    for path in STEP_FILES:
        assert path.exists(), path


def test_step54_script_mentions_phase_and_packet():
    text = read(SCRIPT)
    assert PHASE_STEP in text
    assert PACKET_NAME in text


def test_step54_script_supports_action_all():
    text = read(SCRIPT)
    assert "ValidateSet" in text
    assert '"all"' in text
    assert "Show-Status" in text
    assert "Apply-StepFiles" in text
    assert "Invoke-SmokeTest" in text
    assert "Generate-PlanningPacket" in text


def test_step54_script_uses_literal_path_checks():
    text = read(SCRIPT)
    assert "Test-Path -LiteralPath" in text
    assert "Set-Content -LiteralPath" in text


def test_step54_script_uses_safe_path_joining_without_backslash_regex():
    text = read(SCRIPT)
    assert "Join-SafePath" in text
    assert ".Replace('/', '\\')" in text
    assert "Regex" not in text


def test_step54_apply_is_idempotent_for_same_source_target():
    text = read(SCRIPT)
    assert "source and target are the same file" in text
    assert "OrdinalIgnoreCase" in text


def test_step54_smoke_success_text_is_present():
    text = read(SCRIPT)
    assert "SMOKE TEST PASS: Phase 22 Step 54 $PacketName is present and planning-only." in text


def test_step54_packet_output_includes_required_pass_lines():
    text = read(SCRIPT)
    required = [
        "PASS: planning_only=true",
        "PASS: no_real_bridge_http_client=true",
        "PASS: no_network_transport_implementation=true",
        "PASS: no_bridge_post=true",
        "PASS: no_network_sockets=true",
        "PASS: lacrm_default_mode=dry_run",
        "PASS: live_write_disabled=true",
        "PASS: live_write_unarmed=true",
    ]
    for marker in required:
        assert marker in text


def test_step54_packet_output_includes_required_check_lines():
    text = read(SCRIPT)
    required = [
        "CHECK: implementation_phase_start=not_started",
        "CHECK: authorization_record_creation=false",
        "CHECK: operator_signoff_creation=false",
        "CHECK: operator_approval_creation=false",
        "CHECK: final_approval_creation=false",
        "CHECK: design_closure_record_creation=false",
        "CHECK: closure_decision_creation=false",
        "CHECK: applied_layer_release=not_started",
        "CHECK: source_bucket_alignment=raw_normalized_matched_approved_applied",
    ]
    for marker in required:
        assert marker in text


def test_step54_no_runtime_server_start_tokens_in_public_files():
    forbidden = [
        "uvicorn.run(",
        "FastAPI(",
        "socket.socket(",
        "requests.post(",
        "httpx.post(",
        "sqlite3.connect(",
        "create_engine(",
    ]
    for path in [SCRIPT, PAGE, DOC]:
        text = read(path)
        for token in forbidden:
            assert token not in text, (path, token)


def test_step54_live_write_remains_disabled():
    for path in [SCRIPT, PAGE, DOC]:
        text = read(path)
        assert "lacrm_live_write=true" not in text
        assert "live_write_disabled=false" not in text
        assert "live_write_unarmed=false" not in text


def test_step54_source_bucket_alignment_is_present():
    combined = "\n".join(read(path) for path in [SCRIPT, PAGE, DOC])
    assert "raw_normalized_matched_approved_applied" in combined
    assert "connector_first_operating_core" in combined or "connector-first" in combined
    assert "connector_package_not_separate_product" in combined or "connector package" in combined


def test_step54_closure_deferral_handoff_is_planned_only():
    combined = "\n".join(read(path) for path in [SCRIPT, PAGE, DOC])
    assert "closure_deferral_acceptance_evidence_review_disposition_handoff" in combined
    assert "planned_only" in combined
    assert "handoff_acceptance_evidence_review_disposition_handoff_creation" in combined


def test_step54_ui_page_has_safety_posture():
    text = read(PAGE)
    assert "SAFETY_POSTURE" in text
    assert "planning_only" in text
    assert "no_network_sockets" in text
    assert "live_write_disabled" in text


def test_step54_doc_lists_files_and_do_not_stage_items():
    text = read(DOC)
    for rel in ["scripts/phase22_generate_phase20_network_transport_planning_closure_deferral_acceptance_evidence_review_disposition_handoff_alignment_packet.ps1", "ui/pages/160_Phase20_Network_Transport_Planning_Closure_Deferral_Acceptance_Evidence_Review_Disposition_Handoff_Alignment_Packet.py", "docs/PHASE22_STEP54_PHASE20_NETWORK_TRANSPORT_PLANNING_CLOSURE_DEFERRAL_ACCEPTANCE_EVIDENCE_REVIEW_DISPOSITION_HANDOFF_ALIGNMENT_PACKET.md", "tests/test_phase22_phase20_network_transport_planning_closure_deferral_acceptance_evidence_review_disposition_handoff_alignment_packet.py"]:
        assert rel in text
    for marker in ["data\\unified_pool_service_platform.db", ".env", ".venv", "backups", "bridge folders"]:
        assert marker in text


def test_step54_doc_keeps_planning_only_language():
    text = read(DOC)
    assert "planning_only: true" in text
    assert "no network sockets" in text
    assert "no connector writes" in text
    assert "no database writes" in text


def test_step54_script_menu_is_present():
    text = read(SCRIPT)
    assert "Phase 22 Step 54 menu" in text
    assert "Choose 1-6" in text
    assert "Show server start placeholder only" in text


def test_step54_server_placeholder_prevents_runtime_execution():
    text = read(SCRIPT)
    assert "Server startup is intentionally disabled" in text
    assert "No FastAPI, Streamlit, bridge server, or network socket is started here." in text


def test_step54_expected_branch_is_set():
    text = read(SCRIPT)
    assert "phase22-step54-phase20-network-transport-planning-closure-deferral-acceptance-evidence-review-disposition-handoff-alignment-packet" in text


def test_step54_prior_step_is_set():
    text = read(SCRIPT)
    assert "Phase 22 Step 53 - Phase 20 Network Transport Planning Closure Deferral Acceptance Evidence Review Disposition Alignment Packet" in text


def test_step54_packet_json_name_is_step_specific():
    text = read(SCRIPT)
    assert "phase22_phase20_network_transport_planning_closure_deferral_acceptance_evidence_review_disposition_handoff_alignment_packet" in text
    assert "ConvertTo-Json" in text


def test_step54_does_not_create_approval_or_closure_records():
    combined = "\n".join(read(path) for path in [SCRIPT, PAGE, DOC])
    forbidden = [
        "operator_signoff_creation = $true",
        "operator_approval_creation = $true",
        "final_approval_creation = $true",
        " design_closure_record_creation = $true",
        "closure_decision_creation = $true",
        "handoff_record_creation = $true",
        "handoff_queue_creation = $true",
    ]
    for marker in forbidden:
        assert marker not in combined


def test_step54_page_number_is_correct():
    assert "ui/pages/160_Phase20_Network_Transport_Planning_Closure_Deferral_Acceptance_Evidence_Review_Disposition_Handoff_Alignment_Packet.py" in PAGE.as_posix()


def test_step54_public_files_are_utf8_readable():
    for path in STEP_FILES:
        assert read(path)


def test_step54_no_double_dash_text_in_public_docs():
    for path in [PAGE, DOC]:
        assert "--" not in read(path)


def test_step54_no_invalid_variable_colon_strings():
    text = read(SCRIPT)
    assert "$RelativePath:" not in text
    assert "${RelativePath}:" not in text


def test_step54_pytest_count_anchor():
    test_functions = [line for line in read(TEST_FILE).splitlines() if line.startswith("def test_")]
    assert len(test_functions) == 27


