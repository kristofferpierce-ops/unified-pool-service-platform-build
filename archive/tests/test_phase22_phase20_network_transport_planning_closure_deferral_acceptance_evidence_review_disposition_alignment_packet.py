from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

SCRIPT = ROOT / "scripts/phase22_generate_phase20_network_transport_planning_closure_deferral_acceptance_evidence_review_disposition_alignment_packet.ps1"
UI_PAGE = ROOT / "ui/pages/159_Phase20_Network_Transport_Planning_Closure_Deferral_Acceptance_Evidence_Review_Disposition_Alignment_Packet.py"
DOC = ROOT / "docs/PHASE22_STEP53_PHASE20_NETWORK_TRANSPORT_PLANNING_CLOSURE_DEFERRAL_ACCEPTANCE_EVIDENCE_REVIEW_DISPOSITION_ALIGNMENT_PACKET.md"
TEST_FILE = ROOT / "tests/test_phase22_phase20_network_transport_planning_closure_deferral_acceptance_evidence_review_disposition_alignment_packet.py"

STEP_FILES = [SCRIPT, UI_PAGE, DOC, TEST_FILE]


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_phase22_step53_files_exist():
    for path in STEP_FILES:
        assert path.exists(), path


def test_phase22_step53_script_declares_step_metadata():
    text = read(SCRIPT)
    assert "$StepNumber = 53" in text
    assert "$PhaseNumber = 22" in text
    assert "Phase 22 Step 53 - Phase 20 Network Transport Planning Closure Deferral Acceptance Evidence Review Disposition Alignment Packet" in text


def test_phase22_step53_script_declares_prior_step():
    text = read(SCRIPT)
    assert "Phase 22 Step 52 - Phase 20 Network Transport Planning Closure Deferral Resolution Disposition Handoff Acceptance Evidence Review Alignment Packet" in text


def test_phase22_step53_expected_branch_is_present():
    assert "phase22-step53-phase20-network-transport-planning-closure-deferral-acceptance-evidence-review-disposition-alignment-packet" in read(SCRIPT)


def test_phase22_step53_menu_labels_phase_and_step():
    text = read(SCRIPT)
    assert "Phase 22 Step 53 menu" in text
    assert "Smoke test Phase 22 Step 53" in text


def test_phase22_step53_supports_optimized_actions():
    text = read(SCRIPT)
    for token in ['"status"', '"apply"', '"smoke"', '"packet"', '"server"', '"all"']:
        assert token in text


def test_phase22_step53_smoke_text_is_present():
    assert "SMOKE TEST PASS: Phase 22 Step 53 Phase 20 Network Transport Planning Closure Deferral Acceptance Evidence Review Disposition Alignment Packet is present and planning-only." in read(SCRIPT)


def test_phase22_step53_step_files_are_referenced_by_launcher():
    text = read(SCRIPT)
    for rel in [
        "scripts/phase22_generate_phase20_network_transport_planning_closure_deferral_acceptance_evidence_review_disposition_alignment_packet.ps1",
        "ui/pages/159_Phase20_Network_Transport_Planning_Closure_Deferral_Acceptance_Evidence_Review_Disposition_Alignment_Packet.py",
        "docs/PHASE22_STEP53_PHASE20_NETWORK_TRANSPORT_PLANNING_CLOSURE_DEFERRAL_ACCEPTANCE_EVIDENCE_REVIEW_DISPOSITION_ALIGNMENT_PACKET.md",
        "tests/test_phase22_phase20_network_transport_planning_closure_deferral_acceptance_evidence_review_disposition_alignment_packet.py",
    ]:
        assert rel in text


def test_phase22_step53_uses_safe_path_joining():
    text = read(SCRIPT)
    assert "Join-RepoPath" in text
    assert "Normalize-RelativePath" in text
    assert "Replace([string][char]92" in text


def test_phase22_step53_launcher_avoids_regex_backslash_normalizer():
    text = read(SCRIPT)
    assert "-replace" not in text
    assert "Replace([string][char]92" in text


def test_phase22_step53_planning_only_flags_are_true():
    text = read(SCRIPT)
    for token in [
        "planning_only = $true",
        "no_platform_db_mutation = $true",
        "no_bridge_mutation = $true",
        "no_real_bridge_http_client = $true",
        "no_network_transport_implementation = $true",
        "no_bridge_post = $true",
        "no_network_sockets = $true",
        "no_execution_implementation = $true",
    ]:
        assert token in text


def test_phase22_step53_approval_creation_flags_are_false():
    text = read(SCRIPT)
    for token in [
        "authorization_record_creation = $false",
        "operator_signoff_creation = $false",
        "operator_approval_creation = $false",
        "final_approval_creation = $false",
        "design_closure_record_creation = $false",
        "closure_decision_creation = $false",
    ]:
        assert token in text


def test_phase22_step53_acceptance_review_disposition_is_not_created():
    text = read(SCRIPT)
    for token in [
        "handoff_acceptance_evidence_review_disposition_record_creation = $false",
        "handoff_acceptance_evidence_review_disposition_approval_creation = $false",
        "handoff_acceptance_evidence_review_disposition_execution = $false",
    ]:
        assert token in text


def test_phase22_step53_lacrm_stays_dry_run():
    text = read(SCRIPT)
    assert 'lacrm_default_mode = "dry_run"' in text
    assert "lacrm_live_write = $false" in text
    assert "live_write_disabled = $true" in text
    assert "live_write_unarmed = $true" in text


def test_phase22_step53_no_runtime_network_tokens_in_public_files():
    public_text = "\n".join(read(path) for path in [UI_PAGE, DOC])
    for token in [
        "requests.post(",
        "httpx.post(",
        "socket.socket(",
        "uvicorn.run(",
        "streamlit run",
        "Start-Process uvicorn",
    ]:
        assert token not in public_text


def test_phase22_step53_no_sensitive_values_in_public_files():
    public_text = "\n".join(read(path) for path in [SCRIPT, UI_PAGE, DOC])
    for token in [
        "RC_CLIENT_SECRET",
        "LACRM_API_KEY",
        "FRESHBOOKS_CLIENT_SECRET",
        "sk_live_",
        "xoxb-",
    ]:
        assert token not in public_text


def test_phase22_step53_packet_generation_is_backup_only():
    text = read(SCRIPT)
    assert 'Join-Path $ResolvedRepoRoot "backups"' in text
    assert "phase22_step53_acceptance_evidence_review_disposition_packet.json" in text
    assert "ConvertTo-Json" in text


def test_phase22_step53_packet_prints_required_pass_lines():
    text = read(SCRIPT)
    for token in [
        "PASS: planning_only=true",
        "PASS: no_real_bridge_http_client=true",
        "PASS: no_network_transport_implementation=true",
        "PASS: no_bridge_post=true",
        "PASS: no_network_sockets=true",
        "PASS: lacrm_default_mode=dry_run",
        "PASS: live_write_disabled=true",
        "PASS: live_write_unarmed=true",
        "PASS: closure_deferral_acceptance_evidence_review_disposition=planned_only",
    ]:
        assert token in text


def test_phase22_step53_packet_prints_required_check_lines():
    text = read(SCRIPT)
    for token in [
        "CHECK: implementation_phase_start=not_started",
        "CHECK: authorization_record_creation=false",
        "CHECK: operator_signoff_creation=false",
        "CHECK: operator_approval_creation=false",
        "CHECK: final_approval_creation=false",
        "CHECK: design_closure_record_creation=false",
        "CHECK: closure_decision_creation=false",
        "CHECK: applied_layer_release=not_started",
    ]:
        assert token in text


def test_phase22_step53_doc_declares_no_write_scope():
    text = read(DOC)
    for phrase in [
        "No platform database mutation",
        "No bridge database mutation",
        "No real bridge HTTP client",
        "No handoff acceptance evidence review disposition record creation",
        "LACRM default mode remains `dry_run`",
    ]:
        assert phrase in text


def test_phase22_step53_doc_expected_pytest_count_is_current():
    assert "27 passed" in read(DOC)


def test_phase22_step53_ui_is_planning_only():
    text = read(UI_PAGE)
    assert "Planning-only" in text
    assert '"planning_only": True' in text
    assert '"handoff_acceptance_evidence_review_disposition_record_creation": False' in text
    assert '"handoff_acceptance_evidence_review_disposition_execution": False' in text


def test_phase22_step53_ui_has_operator_note():
    text = read(UI_PAGE)
    assert "Operator note" in text
    assert "approval" in text.lower()
    assert "later authorized phase" in text


def test_phase22_step53_source_bucket_alignment_is_preserved():
    text = read(DOC) + read(SCRIPT)
    assert "raw to normalized to matched to approved to applied" in text.lower()
    assert "connector_package_not_separate_product" in text


def test_phase22_step53_test_file_uses_repo_relative_paths():
    text = read(TEST_FILE)
    assert "STEP_FILES" in text
    assert "Path(__file__).resolve().parents[1]" in text


def test_phase22_step53_uses_step_159_ui_page():
    assert UI_PAGE.name.startswith("159_")
    assert "Acceptance_Evidence_Review_Disposition_Alignment_Packet" in UI_PAGE.name


def test_phase22_step53_public_files_separate_review_from_approval():
    public_text = "\n".join(read(path).lower() for path in [SCRIPT, UI_PAGE, DOC])
    assert "review disposition" in public_text
    assert "approval requires a later authorized phase" in public_text
    assert "handoff_acceptance_evidence_review_disposition_approval_creation = $false" in read(SCRIPT)
