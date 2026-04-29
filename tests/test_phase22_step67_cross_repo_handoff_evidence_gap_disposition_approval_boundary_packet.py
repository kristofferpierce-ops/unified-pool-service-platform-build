from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

SCRIPT_REL = "scripts/phase22_step67_cross_repo_handoff_evidence_gap_disposition_approval_boundary_packet.ps1"
PAGE_REL = "ui/pages/173_Phase20_Network_Transport_Planning_Cross_Repo_Handoff_Evidence_Gap_Disposition_Approval_Boundary_Packet.py"
DOC_REL = "docs/PHASE22_STEP67_CROSS_REPO_HANDOFF_EVIDENCE_GAP_DISPOSITION_APPROVAL_BOUNDARY_PACKET.md"
TEST_REL = "tests/test_phase22_step67_cross_repo_handoff_evidence_gap_disposition_approval_boundary_packet.py"

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


def test_step67_files_exist():
    for path in PUBLIC_FILES:
        assert path.exists(), path


def test_step67_script_mentions_phase_and_step():
    text = read(SCRIPT)
    assert "Phase 22 Step 67" in text
    assert "$StepNumber = 67" in text
    assert "Cross-Repo Handoff Evidence Gap Disposition Approval Boundary Packet" in text


def test_step67_page_number_is_correct():
    assert PAGE.as_posix().endswith(
        "ui/pages/173_Phase20_Network_Transport_Planning_Cross_Repo_Handoff_Evidence_Gap_Disposition_Approval_Boundary_Packet.py"
    )


def test_step67_doc_title_is_correct():
    text = read(DOC)
    assert "# Phase 22 Step 67 - Phase 20 Network Transport Planning Cross-Repo Handoff Evidence Gap Disposition Approval Boundary Packet" in text


def test_step67_prior_step_is_step66():
    text = read(SCRIPT) + "\n" + read(DOC)
    assert "Phase 22 Step 66 - Phase 20 Network Transport Planning Cross-Repo Handoff Evidence Gap Disposition Review Packet" in text
    assert "CHECK: prior_step=Phase 22 Step 66" in text


def test_step67_launcher_supports_action_all():
    text = read(SCRIPT)
    assert '[ValidateSet("menu", "status", "apply", "smoke", "packet", "all")]' in text
    assert '"all"' in text
    assert "Show-Status" in text
    assert "Apply-StepFiles" in text
    assert "Test-Smoke" in text
    assert "New-Packet" in text


def test_step67_uses_literal_and_safe_paths():
    text = read(SCRIPT)
    assert "Test-SafePath" in text
    assert "Test-Path -LiteralPath" in text
    assert "Join-SafePath" in text
    assert "Normalize-RelativePath" in text
    assert "Resolve-RepoRoot" in text
    assert "Parent-workspace safe: true" in text


def test_step67_is_planning_only():
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


def test_step67_keeps_phase23_closed():
    text = combined_public_text()
    required = [
        "phase23_start",
        "phase23_branch_creation",
        "implementation_queue_creation",
        "implementation_ready_transition",
        "implementation_phase_start",
        "phase23_start_boundary_creation",
    ]
    for marker in required:
        assert marker in text


def test_step67_disables_cross_repo_mutation():
    text = combined_public_text()
    required = [
        "cross_repo_write",
        "cross_repo_mutation",
        "external_repo_push",
        "cross_repo_branch_change",
        "cross_repo_file_write",
        "sibling_repo_mutation",
        "cross_repo_validation_write",
    ]
    for marker in required:
        assert marker in text


def test_step67_disables_evidence_collection_decisions_and_approvals():
    text = combined_public_text()
    required = [
        "evidence_gap_disposition_approval_boundary_mode",
        "handoff_evidence_gap_disposition_approval_boundary_record_creation",
        "handoff_evidence_collection_execution",
        "handoff_evidence_gap_disposition_approval_boundary_write",
        "evidence_gap_disposition_decision_creation",
        "evidence_gap_disposition_approval_creation",
        "evidence_gap_approval_record_creation",
        "evidence_gap_remediation_mutation",
        "evidence_gap_resolution_execution",
    ]
    for marker in required:
        assert marker in text


def test_step67_keeps_lacrm_dry_run():
    text = combined_public_text()
    assert "dry_run" in text
    assert "lacrm_live_write" in text
    assert "live_write_disabled" in text
    assert "live_write_unarmed" in text


def test_step67_contains_parent_workspace_commands():
    text = read(DOC)
    assert 'C:\\Users\\krist\\Desktop\\unified_pool_service_platform_build' in text
    assert "git -C $Repo" in text
    assert "python -m pytest (Join-Path $Repo" in text
    assert "INSTALL_PHASE22_STEP67_SINGLE_FILE" in text


def test_step67_menu_has_expected_options():
    text = read(SCRIPT)
    assert "Phase 22 Step 67 menu" in text
    assert "Show status / verify paths" in text
    assert "Smoke test Phase 22 Step 67" in text
    assert "Show server start placeholder only" in text
    assert "Generate Phase 22 Step 67 cross-repo handoff evidence gap disposition approval boundary packet" in text


def test_step67_expected_smoke_success_text_present():
    text = read(SCRIPT)
    expected = (
        "SMOKE TEST PASS: Phase 22 Step 67 Phase 20 Network Transport Planning "
        "Cross-Repo Handoff Evidence Gap Disposition Approval Boundary Packet is present and planning-only."
    )
    assert expected in text


def test_step67_expected_packet_output_in_doc_and_script():
    combined = read(DOC) + "\n" + read(SCRIPT)
    required = [
        "PASS: cross_repo_write=false",
        "PASS: cross_repo_mutation=false",
        "PASS: external_repo_push=false",
        "PASS: evidence_gap_disposition_approval_boundary_mode=reference_only",
        "PASS: handoff_evidence_gap_disposition_approval_boundary_write=false",
        "PASS: evidence_gap_disposition_decision_creation=false",
        "PASS: evidence_gap_disposition_approval_creation=false",
        "PASS: phase23_start=false",
        "CHECK: prior_step=Phase 22 Step 66",
        "CHECK: phase23_start=not_started",
        "CHECK: evidence_gap_disposition_approval_boundary_mode=reference_only",
        "CHECK: parent_workspace_launcher=safe",
        "CHECK: packet_json=",
    ]
    for marker in required:
        assert marker in combined


def test_step67_does_not_create_phase23_or_implementation():
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
        "implementation_ready_transition: true",
        "implementation_ready_transition = true",
    ]
    for marker in forbidden:
        assert marker not in text


def test_step67_does_not_enable_network_or_bridge_runtime():
    text = combined_runtime_text().lower()
    forbidden = [
        "no_real_bridge_http_client: false",
        "no_network_transport_implementation: false",
        "no_bridge_post: false",
        "no_network_sockets: false",
        "no_execution_implementation: false",
        "invoke-restmethod",
        "invoke-webrequest",
        "system.net.http.httpclient",
        "system.net.sockets.tcpclient",
        "requests.post",
        "streamlit run",
        "uvicorn",
    ]
    for marker in forbidden:
        assert marker not in text


def test_step67_does_not_write_to_external_repos():
    text = combined_runtime_text().lower()
    forbidden = [
        "cross_repo_write: true",
        "cross_repo_write = true",
        "cross_repo_mutation: true",
        "cross_repo_mutation = true",
        "external_repo_push: true",
        "external_repo_push = true",
        "cross_repo_branch_change: true",
        "cross_repo_file_write: true",
        "sibling_repo_mutation: true",
        "cross_repo_validation_write: true",
    ]
    for marker in forbidden:
        assert marker not in text


def test_step67_does_not_collect_decide_approve_or_remediate_evidence():
    text = combined_runtime_text().lower()
    forbidden = [
        "handoff_evidence_collection_execution: true",
        "handoff_evidence_collection_execution = true",
        "handoff_evidence_gap_disposition_approval_boundary_write: true",
        "handoff_evidence_gap_disposition_approval_boundary_write = true",
        "evidence_gap_disposition_decision_creation: true",
        "evidence_gap_disposition_decision_creation = true",
        "evidence_gap_disposition_approval_creation: true",
        "evidence_gap_disposition_approval_creation = true",
        "evidence_gap_approval_record_creation: true",
        "evidence_gap_approval_record_creation = true",
        "evidence_gap_remediation_mutation: true",
        "evidence_gap_remediation_mutation = true",
        "evidence_gap_resolution_execution: true",
        "evidence_gap_resolution_execution = true",
        "handoff_evidence_gap_disposition_approval_boundary_record_creation: true",
        "handoff_evidence_gap_disposition_approval_boundary_record_creation = true",
    ]
    for marker in forbidden:
        assert marker not in text


def test_step67_does_not_create_approvals_or_closure_records():
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
        "authorization_record_creation: true",
        "authorization_record_creation = true",
    ]
    for marker in forbidden:
        assert marker not in text


def test_step67_packet_generates_json_under_backups():
    text = read(SCRIPT)
    assert "backups" in text
    assert "phase22_step67_cross_repo_handoff_evidence_gap_disposition_approval_boundary_packet" in text
    assert "ConvertTo-Json" in text
    assert "Set-Content -LiteralPath" in text


def test_step67_expected_branch_is_short():
    text = read(SCRIPT)
    branch = "phase22-step67-cross-repo-handoff-evidence-gap-disposition-approval-boundary"
    assert branch in text
    assert len(branch) < 80


def test_step67_source_zip_filename_not_required_by_launcher():
    text = read(SCRIPT)
    assert "phase22_step67_source(1).zip" not in text
    assert "phase22_step67_source.zip" not in text
    assert "single-file installer" in text.lower()


def test_step67_installer_paths_are_short():
    for rel in [SCRIPT_REL, PAGE_REL, DOC_REL, TEST_REL]:
        assert len(rel) < 150


def test_step67_no_server_start_claim():
    text = combined_public_text().lower()
    assert "no fastapi" in text or "no fastapi or streamlit" in text
    assert "no platform database" in text or "no_platform_db_mutation" in text
    assert "server startup is intentionally disabled" in text
