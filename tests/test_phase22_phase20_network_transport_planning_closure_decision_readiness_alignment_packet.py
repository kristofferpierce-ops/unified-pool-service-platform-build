from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

STEP_SCRIPT = ROOT / "scripts" / "phase22_generate_phase20_network_transport_planning_closure_decision_readiness_alignment_packet.ps1"
STEP_UI = ROOT / "ui" / "pages" / "146_Phase20_Network_Transport_Planning_Closure_Decision_Readiness_Alignment_Packet.py"
STEP_DOC = ROOT / "docs" / "PHASE22_STEP40_PHASE20_NETWORK_TRANSPORT_PLANNING_CLOSURE_DECISION_READINESS_ALIGNMENT_PACKET.md"
STEP_TEST = ROOT / "tests" / "test_phase22_phase20_network_transport_planning_closure_decision_readiness_alignment_packet.py"

STEP_FILES = [STEP_SCRIPT, STEP_UI, STEP_DOC, STEP_TEST]
PUBLIC_FILES = [STEP_SCRIPT, STEP_UI, STEP_DOC]


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_phase22_step40_files_exist():
    for path in STEP_FILES:
        assert path.exists(), path


def test_phase22_step40_identity_and_prior_step_are_correct():
    text = read(STEP_SCRIPT)
    assert "$StepNumber = 40" in text
    assert "$PhaseNumber = 22" in text
    assert "Phase 22 Step 40 - Phase 20 Network Transport Planning Closure Decision Readiness Alignment Packet" in text
    assert "Phase 22 Step 39 - Phase 20 Network Transport Planning Closure Review Board Alignment Packet" in text


def test_phase22_step40_expected_branch_and_slug_are_correct():
    text = read(STEP_SCRIPT)
    assert "phase22-step40-phase20-network-transport-planning-closure-decision-readiness-alignment-packet" in text
    assert "phase22_phase20_network_transport_planning_closure_decision_readiness_alignment_packet" in text


def test_phase22_step40_optimized_action_all_is_supported():
    text = read(STEP_SCRIPT)
    assert "-Action status, apply, smoke, packet, all" in text
    assert '"all" {' in text
    assert "Copy-StepFiles -Root $Root" in text
    assert "Test-Smoke -Root $Root" in text
    assert "New-PlanningPacket -Root $Root" in text


def test_phase22_step40_core_safety_flags_are_present():
    text = read(STEP_SCRIPT)
    required = [
        "planning_only = $true",
        "no_platform_db_mutation = $true",
        "no_bridge_mutation = $true",
        "no_real_bridge_http_client = $true",
        "no_network_transport_implementation = $true",
        "no_bridge_post = $true",
        "no_network_sockets = $true",
        "no_execution_implementation = $true",
        "lacrm_default_mode = \"dry_run\"",
        "lacrm_live_write = $false",
        "live_write_disabled = $true",
        "live_write_unarmed = $true",
    ]
    for item in required:
        assert item in text


def test_phase22_step40_blocks_approval_and_implementation_records():
    text = read(STEP_SCRIPT)
    required = [
        "authorization_record_creation = $false",
        "operator_signoff_creation = $false",
        "operator_approval_creation = $false",
        "final_approval_creation = $false",
        "design_closure_record_creation = $false",
        "implementation_queue_creation = $false",
        "implementation_release_authorization = $false",
        "implementation_phase_start = \"not_started\"",
    ]
    for item in required:
        assert item in text


def test_phase22_step40_blocks_closure_decision_execution():
    text = read(STEP_SCRIPT)
    required = [
        "closure_decision_record_creation = $false",
        "closure_decision_approval = $false",
        "closure_decision_application = $false",
        "closure_decision_finalization = $false",
        "planning_to_implementation_transition = $false",
        "implementation_release_decision = $false",
    ]
    for item in required:
        assert item in text


def test_phase22_step40_closure_decision_alignment_values_are_documented():
    text = read(STEP_SCRIPT)
    required = [
        "closure_decision_readiness_scope = \"planning_packet_only\"",
        "planning_lane_status = \"closure_decision_readiness_documented_not_decided\"",
        "prior_closure_review_board_alignment = \"Phase 22 Step 39\"",
        "closure_decision_readiness_status = \"alignment_only_no_decision_no_release_no_transition\"",
    ]
    for item in required:
        assert item in text


def test_phase22_step40_source_bucket_and_connector_guardrails_remain():
    text = read(STEP_SCRIPT)
    assert "source_bucket_chain = \"raw_to_normalized_to_matched_to_approved_to_applied\"" in text
    assert "connector_first_operating_core = \"planned_reference_only\"" in text
    assert "bridge_route_surface_preservation = \"required\"" in text
    assert "connector_package_absorption = \"planned_not_started\"" in text
    assert "shared_database_merge = \"deferred_until_domain_model_explicit\"" in text


def test_phase22_step40_server_placeholder_is_non_runtime_only():
    text = read(STEP_SCRIPT)
    assert "Server startup is intentionally disabled" in text
    assert "No FastAPI, Streamlit, bridge server, ngrok tunnel, or network socket is started here." in text
    assert "does not decide, approve, queue, close, release, transition, or start implementation" in text


def test_phase22_step40_smoke_success_text_is_exact():
    text = read(STEP_SCRIPT)
    assert "SMOKE TEST PASS: Phase 22 Step 40 Phase 20 Network Transport Planning Closure Decision Readiness Alignment Packet is present and planning-only." in text


def test_phase22_step40_packet_output_contains_expected_pass_lines():
    text = read(STEP_SCRIPT)
    required = [
        "PASS: closure_decision_record_creation=false",
        "PASS: closure_decision_approval=false",
        "PASS: closure_decision_application=false",
        "PASS: closure_decision_finalization=false",
        "PASS: planning_to_implementation_transition=false",
        "PASS: implementation_release_decision=false",
    ]
    for item in required:
        assert item in text


def test_phase22_step40_packet_output_contains_expected_check_lines():
    text = read(STEP_SCRIPT)
    required = [
        "CHECK: closure_decision_record_creation=not_created",
        "CHECK: closure_decision_approval=not_granted",
        "CHECK: closure_decision_application=not_applied",
        "CHECK: closure_decision_finalization=not_finalized",
        "CHECK: planning_to_implementation_transition=not_started",
        "CHECK: implementation_release_decision=not_made",
    ]
    for item in required:
        assert item in text


def test_phase22_step40_public_files_do_not_contain_forbidden_runtime_tokens():
    forbidden = [
        "lacrm_live_" + "write=true",
        "live_write_" + "disabled=false",
        "live_write_" + "unarmed=false",
        "planning_" + "only=false",
        "no_network_" + "sockets=false",
        "no_bridge_" + "post=false",
        "no_real_bridge_" + "http_client=false",
        "implementation_phase_" + "start=true",
        "authorization_record_" + "creation=true",
        "operator_" + "signoff_creation=true",
        "operator_" + "approval_creation=true",
        "final_" + "approval_creation=true",
        "design_closure_record_" + "creation=true",
        "closure_decision_record_" + "creation=true",
        "closure_decision_" + "approval=true",
        "closure_decision_" + "application=true",
        "closure_decision_" + "finalization=true",
        "planning_to_implementation_" + "transition=true",
        "implementation_release_" + "decision=true",
    ]
    for path in PUBLIC_FILES:
        text = read(path)
        for token in forbidden:
            assert token not in text, f"{token} found in {path}"


def test_phase22_step40_ui_page_has_planning_only_boundary():
    text = read(STEP_UI)
    assert "Phase 22 Step 40" in text
    assert "Closure Decision Readiness" in text
    assert "does not create a closure decision" in text
    assert "planning_to_implementation_transition" in text
    assert "shared_database_merge" in text


def test_phase22_step40_doc_contains_run_and_commit_scope():
    text = read(STEP_DOC)
    assert "Phase 22 Step 40" in text
    assert "-Action all" in text
    assert "SMOKE TEST PASS: Phase 22 Step 40" in text
    assert "Only the four Phase 22 Step 40 files should be staged." in text
    assert "data/unified_pool_service_platform.db" in text


def test_phase22_step40_copy_is_idempotent_for_same_source_and_target():
    text = read(STEP_SCRIPT)
    assert "source and target are the same file" in text
    assert "Get-FullPathSafe" in text
    assert "Test-Path -LiteralPath" in text
