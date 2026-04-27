from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]

SCRIPT = REPO_ROOT / "scripts" / "phase22_generate_phase20_network_transport_planning_handoff_dossier_alignment_packet.ps1"
UI_PAGE = REPO_ROOT / "ui" / "pages" / "143_Phase20_Network_Transport_Planning_Handoff_Dossier_Alignment_Packet.py"
DOC = REPO_ROOT / "docs" / "PHASE22_STEP37_PHASE20_NETWORK_TRANSPORT_PLANNING_HANDOFF_DOSSIER_ALIGNMENT_PACKET.md"
TEST_FILE = Path(__file__)

STEP_FILES = [SCRIPT, UI_PAGE, DOC, TEST_FILE]
PUBLIC_FILES = [SCRIPT, UI_PAGE, DOC]


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_phase22_step37_files_exist() -> None:
    for path in STEP_FILES:
        assert path.exists(), f"Missing expected file: {path}"


def test_phase22_step37_title_and_number_are_declared() -> None:
    combined = "\n".join(read(path) for path in PUBLIC_FILES)

    assert "Phase 22 Step 37" in combined
    assert "Handoff Dossier Alignment Packet" in combined


def test_phase22_step37_launcher_supports_optimized_action_all() -> None:
    script_text = read(SCRIPT)

    assert '[ValidateSet("menu", "status", "apply", "smoke", "packet", "all", "exit")]' in script_text
    assert "Optimized launcher actions: -Action status, apply, smoke, packet, all" in script_text
    assert 'Invoke-Action -Root $EffectiveRepoRoot -SelectedAction $Action' in script_text


def test_phase22_step37_launcher_is_path_safe_and_idempotent() -> None:
    script_text = read(SCRIPT)

    assert "Test-Path -LiteralPath" in script_text
    assert "Copy-Item -LiteralPath" in script_text
    assert "source and target are the same file" in script_text
    assert "Remove-ControlChars" in script_text
    assert "Get-FullPathSafe" in script_text
    assert "{0}_{1}" in script_text


def test_phase22_step37_planning_only_guardrails_are_declared() -> None:
    combined = "\n".join(read(path) for path in PUBLIC_FILES)

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


def test_phase22_step37_handoff_dossier_base_guards_are_plan_only() -> None:
    combined = "\n".join(read(path) for path in PUBLIC_FILES)

    assert "deployment_execution" in combined
    assert "deployment_start" in combined
    assert "runtime_server_start" in combined
    assert "network_transport_start" in combined
    assert "deployment_readiness_plan_only" in combined
    assert "planning_handoff_dossier_plan_only" in combined
    assert "planning_exit_approval" in combined
    assert "implementation_exit_approval" in combined
    assert "planning_exit_record_creation" in combined
    assert "ready_for_handoff_review_not_approved" in combined


def test_phase22_step37_prior_gate_chain_is_preserved() -> None:
    combined = "\n".join(read(path) for path in PUBLIC_FILES)

    for token in [
        "Phase 22 Step 30",
        "Phase 22 Step 31",
        "Phase 22 Step 32",
        "Phase 22 Step 33",
        "Phase 22 Step 34",
        "Phase 22 Step 35",
        "Phase 22 Step 36",
    ]:
        assert token in combined


def test_phase22_step37_rollout_alignment_is_preserved() -> None:
    combined = "\n".join(read(path) for path in PUBLIC_FILES)

    assert "raw_to_normalized_to_matched_to_approved_to_applied" in combined
    assert "source-bucket" in combined or "source_bucket" in combined
    assert "canonical_event_ledger" in combined
    assert "expected_actual_variance" in combined
    assert "driver_attribution" in combined
    assert "probabilistic_calibration" in combined
    assert "pattern_detection" in combined
    assert "recommendation_engine" in combined
    assert "bridge_route_surface_preservation" in combined
    assert "shared_database_merge" in combined
    assert "connector_package_absorption" in combined


def test_phase22_step37_forbidden_runtime_tokens_absent_from_public_files() -> None:
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
    ]

    for path in PUBLIC_FILES:
        text = read(path)
        for token in forbidden:
            assert token not in text, f"Forbidden token {token!r} found in {path}"


def test_phase22_step37_packet_generation_mentions_expected_pass_checks() -> None:
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
        "CHECK: implementation_phase_start=not_started",
        "CHECK: deployment_readiness_checkpoint=documented_not_approved",
        "CHECK: planning_lane_status=ready_for_handoff_review_not_approved",
        "CHECK: planning_exit_record_creation=not_created",
        "CHECK: handoff_dossier_record_creation=not_created",
        "CHECK: implementation_queue_creation=not_created",
        "CHECK: packet_json=$PacketPath",
    ]

    for token in expected:
        assert token in script_text


def test_phase22_step37_streamlit_page_is_read_only() -> None:
    ui_text = read(UI_PAGE)

    assert "st.set_page_config" in ui_text
    assert "st.title" in ui_text
    assert "streamlit" in ui_text
    assert "requests." not in ui_text
    assert "sqlite3" not in ui_text
    assert "create_engine" not in ui_text


def test_phase22_step37_document_lists_all_added_files() -> None:
    doc_text = read(DOC)

    for rel_path in [
        'scripts\\phase22_generate_phase20_network_transport_planning_handoff_dossier_alignment_packet.ps1',
        'ui\\pages\\143_Phase20_Network_Transport_Planning_Handoff_Dossier_Alignment_Packet.py',
        'docs\\PHASE22_STEP37_PHASE20_NETWORK_TRANSPORT_PLANNING_HANDOFF_DOSSIER_ALIGNMENT_PACKET.md',
        'tests\\test_phase22_phase20_network_transport_planning_handoff_dossier_alignment_packet.py',
    ]:
        assert rel_path in doc_text


def test_phase22_step37_no_approval_creation_or_execution_start() -> None:
    combined = "\n".join(read(path) for path in PUBLIC_FILES)

    assert "operator_signoff_creation = $false" in combined or "operator_signoff_creation | false" in combined
    assert "operator_approval_creation = $false" in combined or "operator_approval_creation | false" in combined
    assert "final_approval_creation = $false" in combined or "final_approval_creation | false" in combined
    assert "design_closure_record_creation = $false" in combined or "design_closure_record_creation | false" in combined
    assert "implementation_phase_start = $false" in combined or "implementation_phase_start | not_started" in combined
    assert "deployment_execution = $false" in combined or "deployment_execution | false" in combined
    assert "planning_exit_approval = $false" in combined or "planning_exit_approval | false" in combined
    assert "implementation_exit_approval = $false" in combined or "implementation_exit_approval | false" in combined
    assert "handoff_dossier_record_creation = $false" in combined or "handoff_dossier_record_creation | false" in combined
    assert "implementation_handoff_execution = $false" in combined or "implementation_handoff_execution | false" in combined
    assert "implementation_queue_creation = $false" in combined or "implementation_queue_creation | false" in combined
    assert "handoff_to_implementation_approval = $false" in combined or "handoff_to_implementation_approval | not_granted" in combined

def test_phase22_step37_launcher_avoids_variable_colon_parser_bug() -> None:
    script_text = read(SCRIPT)

    assert "$RelativePath: $Token" not in script_text
    assert '"SMOKE TEST FAIL: Forbidden token found in {0}: {1}" -f $RelativePath, $Token' in script_text


def test_phase22_step37_handoff_dossier_is_plan_only() -> None:
    combined = "\n".join(read(path) for path in PUBLIC_FILES)

    assert "handoff_dossier_record_creation" in combined
    assert "implementation_handoff_execution" in combined
    assert "implementation_queue_creation" in combined
    assert "handoff_to_implementation_approval" in combined
    assert "planning_handoff_dossier_plan_only" in combined
    assert "ready_for_handoff_review_not_approved" in combined
    assert "not_granted" in combined

