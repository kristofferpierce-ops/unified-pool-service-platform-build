from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
STEP_SCRIPT = REPO_ROOT / "scripts/phase22_generate_phase20_network_transport_planning_closure_deferral_resolution_evidence_alignment_packet.ps1"
UI_PAGE = REPO_ROOT / "ui/pages/150_Phase20_Network_Transport_Planning_Closure_Deferral_Resolution_Evidence_Alignment_Packet.py"
DOC_FILE = REPO_ROOT / "docs/PHASE22_STEP44_PHASE20_NETWORK_TRANSPORT_PLANNING_CLOSURE_DEFERRAL_RESOLUTION_EVIDENCE_ALIGNMENT_PACKET.md"
TEST_FILE = REPO_ROOT / "tests/test_phase22_phase20_network_transport_planning_closure_deferral_resolution_evidence_alignment_packet.py"
STEP_FILES = [STEP_SCRIPT, UI_PAGE, DOC_FILE, TEST_FILE]


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def forbidden_tokens():
    return [
        "lacrm_live" + "_write=true",
        "live_write" + "=true",
        "planning_only" + "=false",
        "no_network" + "_sockets=false",
        "no_bridge" + "_post=false",
        "implementation_phase" + "_start=true",
        "operator_signoff" + "_creation=true",
        "operator_approval" + "_creation=true",
        "final_approval" + "_creation=true",
        "design_closure" + "_record_creation=true",
        "closure_decision" + "_record_creation=true",
        "closure_approval" + "_creation=true",
        "implementation_queue" + "_creation=true",
        "closure_deferral_backlog" + "_record_creation=true",
        "closure_deferral_backlog" + "_queue_creation=true",
        "closure_deferral_resolution" + "_record_creation=true",
        "closure_deferral_resolution" + "_queue_creation=true",
        "closure_deferral_resolution_evidence" + "_record_creation=true",
        "closure_deferral_resolution_evidence" + "_queue_creation=true",
        "closure_resolution" + "_execution=true",
        "source_bucket" + "_writes=true",
        "applied_layer" + "_writes=true",
        "recommendation" + "_execution=true",
        "runtime_pattern" + "_detection=true",
        "bayesian_update" + "_execution=true",
    ]


def test_phase22_step44_files_exist():
    for path in STEP_FILES:
        assert path.exists(), f"Missing {path}"


def test_phase22_step44_launcher_has_expected_title_and_branch():
    text = read(STEP_SCRIPT)
    assert "Phase 22 Step 44 - Phase 20 Network Transport Planning Closure Deferral Resolution Evidence Alignment Packet" in text
    assert "phase22-step44-phase20-network-transport-planning-closure-deferral-resolution-evidence-alignment-packet" in text
    assert "Phase 22 Step 43" in text


def test_phase22_step44_launcher_supports_optimized_actions():
    text = read(STEP_SCRIPT)
    assert 'ValidateSet("menu", "status", "apply", "smoke", "packet", "all")' in text
    assert "Optimized launcher actions: -Action status, apply, smoke, packet, all" in text
    assert '"all"' in text


def test_phase22_step44_launcher_is_path_safe():
    text = read(STEP_SCRIPT)
    assert "Test-Path -LiteralPath" in text
    assert "Copy-Item -LiteralPath" in text
    assert "Get-FullPathSafe" in text
    assert "Remove-ControlCharacters" in text
    assert "source and target are the same file" in text


def test_phase22_step44_launcher_has_planning_safety_flags():
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
        "live_write_disabled = $true",
        "live_write_unarmed = $true",
        "closure_decision_deferred = $true",
        "closure_deferral_backlog_planned = $true",
        "closure_deferral_resolution_criteria_planned = $true",
        "closure_deferral_resolution_evidence_planned = $true",
    ]
    for token in required:
        assert token in text


def test_phase22_step44_launcher_blocks_approval_closure_resolution_evidence_and_queue_creation():
    text = read(STEP_SCRIPT)
    blocked = [
        "authorization_record_creation = $false",
        "operator_signoff_creation = $false",
        "operator_approval_creation = $false",
        "final_approval_creation = $false",
        "design_closure_record_creation = $false",
        "closure_decision_record_creation = $false",
        "closure_approval_creation = $false",
        "implementation_queue_creation = $false",
        "closure_deferral_backlog_record_creation = $false",
        "closure_deferral_backlog_queue_creation = $false",
        "closure_deferral_resolution_record_creation = $false",
        "closure_deferral_resolution_queue_creation = $false",
        "closure_deferral_resolution_evidence_record_creation = $false",
        "closure_deferral_resolution_evidence_queue_creation = $false",
        "closure_resolution_execution = $false",
    ]
    for token in blocked:
        assert token in text


def test_phase22_step44_launcher_generates_packet_under_backups():
    text = read(STEP_SCRIPT)
    assert "backups" in text
    assert "phase22_phase20_network_transport_planning_closure_deferral_resolution_evidence_alignment_packet.json" in text
    assert "ConvertTo-Json -Depth 12" in text
    assert "CHECK: packet_json=$PacketPath" in text


def test_phase22_step44_smoke_success_text_is_present():
    text = read(STEP_SCRIPT)
    assert "SMOKE TEST PASS: Phase 22 Step 44 Phase 20 Network Transport Planning Closure Deferral Resolution Evidence Alignment Packet is present and planning-only." in text


def test_phase22_step44_expected_packet_checks_are_present():
    text = read(STEP_SCRIPT)
    checks = [
        "PASS: planning_only=true",
        "PASS: no_real_bridge_http_client=true",
        "PASS: no_network_transport_implementation=true",
        "PASS: no_bridge_post=true",
        "PASS: no_network_sockets=true",
        "PASS: lacrm_default_mode=dry_run",
        "PASS: live_write_disabled=true",
        "PASS: live_write_unarmed=true",
        "PASS: closure_decision_deferred=true",
        "PASS: closure_deferral_backlog_planned=true",
        "PASS: closure_deferral_resolution_criteria_planned=true",
        "PASS: closure_deferral_resolution_evidence_planned=true",
        "CHECK: closure_decision_record_creation=false",
        "CHECK: closure_approval_creation=false",
        "CHECK: implementation_queue_creation=false",
        "CHECK: closure_deferral_backlog_record_creation=false",
        "CHECK: closure_deferral_backlog_queue_creation=false",
        "CHECK: closure_deferral_resolution_record_creation=false",
        "CHECK: closure_deferral_resolution_queue_creation=false",
        "CHECK: closure_deferral_resolution_evidence_record_creation=false",
        "CHECK: closure_deferral_resolution_evidence_queue_creation=false",
        "CHECK: closure_resolution_execution=false",
        "CHECK: implementation_phase_start=not_started",
        "CHECK: source_bucket_alignment=raw_normalized_matched_approved_applied",
        "CHECK: bridge_absorption_target=connector_package_not_separate_product",
    ]
    for check in checks:
        assert check in text


def test_phase22_step44_forbidden_tokens_are_split_in_launcher():
    text = read(STEP_SCRIPT)
    assert '("lacrm_live" + "_write=true")' in text
    assert '("closure_decision" + "_record_creation=true")' in text
    assert '("closure_deferral_resolution_evidence" + "_record_creation=true")' in text
    assert '("closure_deferral_resolution_evidence" + "_queue_creation=true")' in text
    assert "Forbidden token found in ${RelativePath}: $Token" in text


def test_phase22_step44_doc_mentions_resolution_evidence_not_record_creation():
    text = read(DOC_FILE)
    assert "Closure deferral resolution evidence rule" in text
    assert "does not resolve the deferred closure decision" in text
    assert "Blocked outputs" in text


def test_phase22_step44_doc_contains_rollout_alignment():
    text = read(DOC_FILE)
    assert "connector-first operating core" in text
    assert "raw to normalized to matched to approved to applied" in text
    assert "bridge stabilization before connector-package absorption" in text


def test_phase22_step44_ui_is_read_only_and_planning_only():
    text = read(UI_PAGE)
    assert "read-only" in text
    assert "planning_only" in text
    assert "closure_deferral_resolution_evidence_planned" in text
    assert "does not create closure records" in text


def test_phase22_step44_ui_blocks_runtime_and_writes():
    text = read(UI_PAGE)
    blocked = [
        "no_platform_db_mutation",
        "no_bridge_mutation",
        "no_real_bridge_http_client",
        "no_network_transport_implementation",
        "no_network_sockets",
        "implementation_queue_creation",
        "closure_deferral_resolution_evidence_record_creation",
        "closure_deferral_resolution_evidence_queue_creation",
        "closure_resolution_execution",
        "lacrm_default_mode",
    ]
    for token in blocked:
        assert token in text


def test_phase22_step44_no_forbidden_runtime_tokens_in_public_files():
    for path in [STEP_SCRIPT, UI_PAGE, DOC_FILE]:
        text = read(path)
        for token in forbidden_tokens():
            assert token not in text, f"{token} found in {path}"


def test_phase22_step44_step_file_list_matches_expected_paths():
    text = read(STEP_SCRIPT)
    for rel in ["scripts/phase22_generate_phase20_network_transport_planning_closure_deferral_resolution_evidence_alignment_packet.ps1", "ui/pages/150_Phase20_Network_Transport_Planning_Closure_Deferral_Resolution_Evidence_Alignment_Packet.py", "docs/PHASE22_STEP44_PHASE20_NETWORK_TRANSPORT_PLANNING_CLOSURE_DEFERRAL_RESOLUTION_EVIDENCE_ALIGNMENT_PACKET.md", "tests/test_phase22_phase20_network_transport_planning_closure_deferral_resolution_evidence_alignment_packet.py"]:
        assert rel in text


def test_phase22_step44_manual_menu_is_preserved():
    text = read(STEP_SCRIPT)
    assert "Phase 22 Step 44 menu" in text
    assert "1. Show status / verify paths" in text
    assert "2. Apply Phase 22 Step 44" in text
    assert "3. Smoke test Phase 22 Step 44" in text
    assert "4. Show server start placeholder only" in text
    assert "5. Generate Phase 20 network transport planning closure deferral resolution evidence alignment packet" in text
    assert "6. Exit" in text


def test_phase22_step44_resolution_evidence_is_planning_reference_only():
    text = read(STEP_SCRIPT) + read(DOC_FILE) + read(UI_PAGE)
    assert "planned reference only" in text
    assert "does not authorize implementation" in text or "does not create" in text
    assert "future evidence categories" in text
