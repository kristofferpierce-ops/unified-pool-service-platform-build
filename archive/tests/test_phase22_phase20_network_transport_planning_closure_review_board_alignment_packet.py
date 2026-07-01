from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]

SCRIPT = REPO_ROOT / "scripts" / "phase22_generate_phase20_network_transport_planning_closure_review_board_alignment_packet.ps1"
UI_PAGE = REPO_ROOT / "ui" / "pages" / "145_Phase20_Network_Transport_Planning_Closure_Review_Board_Alignment_Packet.py"
DOC = REPO_ROOT / "docs" / "PHASE22_STEP39_PHASE20_NETWORK_TRANSPORT_PLANNING_CLOSURE_REVIEW_BOARD_ALIGNMENT_PACKET.md"
TEST_FILE = Path(__file__)

STEP_FILES = [SCRIPT, UI_PAGE, DOC, TEST_FILE]
PUBLIC_FILES = [SCRIPT, UI_PAGE, DOC]


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def combined_public_text() -> str:
    return "\n".join(read(path) for path in PUBLIC_FILES)


def test_phase22_step39_files_exist() -> None:
    for path in STEP_FILES:
        assert path.exists(), f"Missing expected file: {path}"


def test_phase22_step39_title_and_number_are_declared() -> None:
    combined = combined_public_text()
    assert "Phase 22 Step 39" in combined
    assert "Closure Review Board Alignment Packet" in combined


def test_phase22_step39_launcher_supports_optimized_action_all() -> None:
    script_text = read(SCRIPT)
    assert '[ValidateSet("menu", "status", "apply", "smoke", "packet", "all", "exit")]' in script_text
    assert "Optimized launcher actions: -Action status, apply, smoke, packet, all" in script_text
    assert 'Invoke-Action -Root $EffectiveRepoRoot -SelectedAction $Action' in script_text


def test_phase22_step39_launcher_is_path_safe_and_idempotent() -> None:
    script_text = read(SCRIPT)
    assert "Test-Path -LiteralPath" in script_text
    assert "Copy-Item -LiteralPath" in script_text
    assert "source and target are the same file" in script_text
    assert "Remove-ControlChars" in script_text
    assert "Get-FullPathSafe" in script_text
    assert "{0}_{1}" in script_text


def test_phase22_step39_planning_only_guardrails_are_declared() -> None:
    combined = combined_public_text()
    required = [
        "planning_only",
        "no_platform_db_mutation",
        "no_bridge_mutation",
        "no_real_bridge_http_client",
        "no_network_transport_implementation",
        "no_bridge_post",
        "no_network_sockets",
        "no_execution_implementation",
        "implementation_phase_start",
        "authorization_record_creation",
        "operator_signoff_creation",
        "operator_approval_creation",
        "final_approval_creation",
        "design_closure_record_creation",
        "lacrm_default_mode",
        "live_write_disabled",
        "live_write_unarmed",
    ]
    for token in required:
        assert token in combined


def test_phase22_step39_review_board_base_guards_are_plan_only() -> None:
    combined = combined_public_text()
    for token in [
        "deployment_execution",
        "deployment_start",
        "runtime_server_start",
        "network_transport_start",
        "deployment_readiness_plan_only",
        "planning_handoff_dossier_plan_only",
        "planning_closure_evidence_plan_only",
        "closure_review_board_plan_only",
        "planning_exit_approval",
        "implementation_exit_approval",
        "planning_exit_record_creation",
        "closure_review_board_alignment_documented_not_approved",
    ]:
        assert token in combined


def test_phase22_step39_prior_gate_chain_is_preserved() -> None:
    combined = combined_public_text()
    for token in [
        "Phase 22 Step 30",
        "Phase 22 Step 31",
        "Phase 22 Step 32",
        "Phase 22 Step 33",
        "Phase 22 Step 34",
        "Phase 22 Step 35",
        "Phase 22 Step 36",
        "Phase 22 Step 37",
        "Phase 22 Step 38",
    ]:
        assert token in combined


def test_phase22_step39_rollout_alignment_is_preserved() -> None:
    combined = combined_public_text()
    assert "raw_to_normalized_to_matched_to_approved_to_applied" in combined
    assert "source-bucket" in combined or "source_bucket" in combined
    for token in [
        "canonical_event_ledger",
        "expected_actual_variance",
        "driver_attribution",
        "probabilistic_calibration",
        "pattern_detection",
        "recommendation_engine",
        "bridge_route_surface_preservation",
        "shared_database_merge",
        "connector_package_absorption",
    ]:
        assert token in combined


def test_phase22_step39_forbidden_runtime_tokens_absent_from_public_files() -> None:
    forbidden = [
        "requests.post(",
        "requests.get(",
        "httpx.",
        "socket.",
        "uvicorn.run(",
        "FastAPI(",
        "subprocess.Popen",
        "sqlite3.connect",
        "Session(",
        "create_engine(",
        "lacrm_live_write=true",
        "live_write_disabled=false",
        "live_write_unarmed=false",
        "planning_only=false",
        "no_network_sockets=false",
        "no_bridge_post=false",
        "implementation_phase_start=true",
        "authorization_record_creation=true",
        "operator_signoff_creation=true",
        "operator_approval_creation=true",
        "final_approval_creation=true",
        "design_closure_record_creation=true",
        "applied_layer_release_execution=true",
        "rollback_execution=true",
        "recovery_execution=true",
        "restore_execution=true",
        "deployment_execution=true",
        "deployment_start=true",
        "runtime_server_start=true",
        "network_transport_start=true",
        "planning_exit_approval=true",
        "implementation_exit_approval=true",
        "handoff_dossier_record_creation=true",
        "implementation_handoff_execution=true",
        "implementation_queue_creation=true",
        "handoff_to_implementation_approval=true",
        "planning_closure_record_creation=true",
        "closure_evidence_record_creation=true",
        "closure_evidence_approval=true",
        "closure_evidence_application=true",
        "implementation_release_authorization=true",
        "closure_review_board_creation=true",
        "closure_review_board_session_start=true",
        "closure_review_board_approval=true",
        "closure_review_board_vote_record_creation=true",
        "closure_review_board_decision_record_creation=true",
        "closure_review_board_release_authorization=true",
    ]
    for path in PUBLIC_FILES:
        text = read(path)
        for token in forbidden:
            assert token not in text, f"Forbidden token {token!r} found in {path}"


def test_phase22_step39_packet_generation_mentions_expected_pass_checks() -> None:
    script_text = read(SCRIPT)
    expected = [
        "PASS: planning_only=true",
        "PASS: no_real_bridge_http_client=true",
        "PASS: no_network_transport_implementation=true",
        "PASS: no_bridge_post=true",
        "PASS: no_network_sockets=true",
        "PASS: lacrm_default_mode=dry_run",
        "PASS: live_write_disabled=true",
        "PASS: live_write_unarmed=true",
        "PASS: deployment_execution=false",
        "PASS: deployment_start=false",
        "PASS: runtime_server_start=false",
        "PASS: planning_exit_approval=false",
        "PASS: implementation_exit_approval=false",
        "PASS: handoff_dossier_record_creation=false",
        "PASS: implementation_handoff_execution=false",
        "PASS: implementation_queue_creation=false",
        "PASS: handoff_to_implementation_approval=false",
        "PASS: planning_closure_record_creation=false",
        "PASS: closure_evidence_record_creation=false",
        "PASS: closure_evidence_approval=false",
        "PASS: closure_evidence_application=false",
        "PASS: implementation_release_authorization=false",
        "PASS: closure_review_board_creation=false",
        "PASS: closure_review_board_session_start=false",
        "PASS: closure_review_board_approval=false",
        "PASS: closure_review_board_vote_record_creation=false",
        "PASS: closure_review_board_decision_record_creation=false",
        "PASS: closure_review_board_release_authorization=false",
        "CHECK: implementation_phase_start=not_started",
        "CHECK: deployment_readiness_checkpoint=documented_not_approved",
        "CHECK: planning_lane_status=closure_review_board_alignment_documented_not_approved",
        "CHECK: planning_closure_record_creation=not_created",
        "CHECK: closure_evidence_record_creation=not_created",
        "CHECK: closure_review_board_creation=not_created",
        "CHECK: closure_review_board_session_start=not_started",
        "CHECK: closure_review_board_approval=not_granted",
        "CHECK: closure_review_board_vote_record_creation=not_created",
        "CHECK: closure_review_board_decision_record_creation=not_created",
        "CHECK: implementation_release_authorization=not_granted",
        "CHECK: packet_json=$PacketPath",
    ]
    for token in expected:
        assert token in script_text


def test_phase22_step39_streamlit_page_is_read_only() -> None:
    ui_text = read(UI_PAGE)
    assert "st.set_page_config" in ui_text
    assert "st.title" in ui_text
    assert "streamlit" in ui_text
    assert "requests." not in ui_text
    assert "sqlite3" not in ui_text
    assert "create_engine" not in ui_text


def test_phase22_step39_document_lists_all_added_files() -> None:
    doc_text = read(DOC)
    for rel_path in [
        r"scripts\phase22_generate_phase20_network_transport_planning_closure_review_board_alignment_packet.ps1",
        r"ui\pages\145_Phase20_Network_Transport_Planning_Closure_Review_Board_Alignment_Packet.py",
        r"docs\PHASE22_STEP39_PHASE20_NETWORK_TRANSPORT_PLANNING_CLOSURE_REVIEW_BOARD_ALIGNMENT_PACKET.md",
        r"tests\test_phase22_phase20_network_transport_planning_closure_review_board_alignment_packet.py",
    ]:
        assert rel_path in doc_text


def test_phase22_step39_no_approval_creation_or_execution_start() -> None:
    combined = combined_public_text()
    checks = [
        "operator_signoff_creation = $false",
        "operator_approval_creation = $false",
        "final_approval_creation = $false",
        "design_closure_record_creation = $false",
        "implementation_phase_start = $false",
        "deployment_execution = $false",
        "planning_exit_approval = $false",
        "implementation_exit_approval = $false",
        "handoff_dossier_record_creation = $false",
        "implementation_handoff_execution = $false",
        "implementation_queue_creation = $false",
        "handoff_to_implementation_approval = $false",
        "planning_closure_record_creation = $false",
        "closure_evidence_record_creation = $false",
        "closure_evidence_approval = $false",
        "implementation_release_authorization = $false",
        "closure_review_board_creation = $false",
        "closure_review_board_session_start = $false",
        "closure_review_board_approval = $false",
        "closure_review_board_vote_record_creation = $false",
        "closure_review_board_decision_record_creation = $false",
        "closure_review_board_release_authorization = $false",
    ]
    for token in checks:
        assert token in combined


def test_phase22_step39_launcher_avoids_variable_colon_parser_bug() -> None:
    script_text = read(SCRIPT)
    assert "$RelativePath: $Token" not in script_text
    assert '"SMOKE TEST FAIL: Forbidden token found in {0}: {1}" -f $RelativePath, $Token' in script_text


def test_phase22_step39_closure_review_board_is_plan_only() -> None:
    combined = combined_public_text()
    for token in [
        "closure_review_board_creation",
        "closure_review_board_session_start",
        "closure_review_board_approval",
        "closure_review_board_vote_record_creation",
        "closure_review_board_decision_record_creation",
        "closure_review_board_release_authorization",
        "closure_review_board_plan_only",
        "closure_review_board_alignment_documented_not_approved",
        "not_granted",
    ]:
        assert token in combined


def test_phase22_step39_expected_branch_and_step_number_are_correct() -> None:
    script_text = read(SCRIPT)
    assert '$StepNumber = 39' in script_text
    assert '$PhaseNumber = 22' in script_text
    assert 'phase22-step39-phase20-network-transport-planning-closure-review-board-alignment-packet' in script_text
    assert "Phase 22 Step 38 - Phase 20 Network Transport Planning Closure Evidence Alignment Packet" in script_text


def test_phase22_step39_does_not_create_board_vote_or_decision_records() -> None:
    combined = combined_public_text()
    for token in [
        "closure_review_board_vote_record_creation = $false",
        "closure_review_board_decision_record_creation = $false",
        "closure_review_board_release_authorization = $false",
        "closure_review_board_vote_record_creation=not_created",
        "closure_review_board_decision_record_creation=not_created",
        "closure_review_board_release_authorization=false",
        "board vote records remain not_created",
    ]:
        assert token in combined
