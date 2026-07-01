from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

SCRIPT = ROOT / "scripts/phase22_generate_phase20_network_transport_planning_closure_deferral_resolution_disposition_handoff_acceptance_evidence_review_alignment_packet.ps1"
UI_PAGE = ROOT / "ui/pages/158_Phase20_Network_Transport_Planning_Closure_Deferral_Resolution_Disposition_Handoff_Acceptance_Evidence_Review_Alignment_Packet.py"
DOC = ROOT / "docs/PHASE22_STEP52_PHASE20_NETWORK_TRANSPORT_PLANNING_CLOSURE_DEFERRAL_RESOLUTION_DISPOSITION_HANDOFF_ACCEPTANCE_EVIDENCE_REVIEW_ALIGNMENT_PACKET.md"
TEST_FILE = ROOT / "tests/test_phase22_phase20_network_transport_planning_closure_deferral_resolution_disposition_handoff_acceptance_evidence_review_alignment_packet.py"

STEP_FILES = [SCRIPT, UI_PAGE, DOC, TEST_FILE]


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_phase22_step52_expected_files_exist():
    for path in STEP_FILES:
        assert path.exists(), f"Missing expected file: {path}"


def test_phase22_step52_script_has_expected_title_and_branch():
    text = read(SCRIPT)
    assert "Phase 22 Step 52 - Phase 20 Network Transport Planning Closure Deferral Resolution Disposition Handoff Acceptance Evidence Review Alignment Packet" in text
    assert "phase22-step52-phase20-network-transport-planning-closure-deferral-resolution-disposition-handoff-acceptance-evidence-review-alignment-packet" in text


def test_phase22_step52_launcher_supports_optimized_actions():
    text = read(SCRIPT)
    for token in ["status", "apply", "smoke", "packet", "server", "all", "menu"]:
        assert token in text


def test_phase22_step52_launcher_is_path_safe():
    text = read(SCRIPT)
    assert "Test-Path -LiteralPath" in text
    assert "Set-Content -LiteralPath" in text
    assert "Get-Content -LiteralPath" in text
    assert "Join-RepoPath" in text
    assert "Normalize-RelativePath" in text
    assert "Replace([string][char]92" in text


def test_phase22_step52_launcher_is_planning_only():
    text = read(SCRIPT)
    for token in [
        "planning_only = $true",
        "no_platform_db_mutation = $true",
        "no_bridge_mutation = $true",
        "no_network_transport_implementation = $true",
        "no_bridge_post = $true",
        "no_network_sockets = $true",
        "no_execution_implementation = $true",
    ]:
        assert token in text


def test_phase22_step52_lacrm_guardrails_are_dry_run_only():
    text = read(SCRIPT)
    assert 'lacrm_default_mode = "dry_run"' in text
    assert "lacrm_live_write = $false" in text
    assert "live_write_disabled = $true" in text
    assert "live_write_unarmed = $true" in text


def test_phase22_step52_acceptance_evidence_review_does_not_create_records():
    text = read(SCRIPT)
    for token in [
        "handoff_acceptance_evidence_review_record_creation = $false",
        "handoff_acceptance_evidence_review_approval_creation = $false",
        "handoff_acceptance_evidence_review_execution = $false",
        "handoff_acceptance_evidence_record_creation = $false",
        "handoff_acceptance_evidence_execution = $false",
        "handoff_queue_creation = $false",
    ]:
        assert token in text


def test_phase22_step52_packet_generation_is_backup_only():
    text = read(SCRIPT)
    assert 'Join-Path $ResolvedRepoRoot "backups"' in text
    assert "ConvertTo-Json" in text
    assert "phase22_step52_acceptance_evidence_review_packet.json" in text


def test_phase22_step52_no_runtime_network_tokens_in_public_files():
    public_text = "\n".join(read(path) for path in [UI_PAGE, DOC])
    forbidden = [
        "requests.post(",
        "httpx.post(",
        "socket.socket(",
        "uvicorn.run(",
        "streamlit run",
        "subprocess.Popen",
        "Start-Process uvicorn",
    ]
    for token in forbidden:
        assert token not in public_text


def test_phase22_step52_doc_declares_no_write_scope():
    text = read(DOC)
    for phrase in [
        "No platform database mutation",
        "No bridge database mutation",
        "No real bridge HTTP client",
        "No handoff acceptance evidence review record creation",
        "LACRM default mode remains `dry_run`",
    ]:
        assert phrase in text


def test_phase22_step52_ui_is_planning_only():
    text = read(UI_PAGE)
    assert "Planning-only" in text
    assert '"planning_only": True' in text
    assert '"handoff_acceptance_evidence_review_record_creation": False' in text
    assert '"handoff_acceptance_evidence_review_execution": False' in text
    assert '"lacrm_default_mode": "dry_run"' in text


def test_phase22_step52_ui_has_operator_context():
    text = read(UI_PAGE)
    assert "Operator note" in text
    assert "acceptance-evidence review criteria" in text


def test_phase22_step52_source_bucket_alignment_preserved():
    text = read(DOC) + read(SCRIPT)
    assert "raw to normalized to matched to approved to applied" in text.lower()
    assert "connector_package_not_separate_product" in text


def test_phase22_step52_expected_step_files_are_referenced_by_launcher():
    text = read(SCRIPT)
    for rel in [
        "scripts/phase22_generate_phase20_network_transport_planning_closure_deferral_resolution_disposition_handoff_acceptance_evidence_review_alignment_packet.ps1",
        "ui/pages/158_Phase20_Network_Transport_Planning_Closure_Deferral_Resolution_Disposition_Handoff_Acceptance_Evidence_Review_Alignment_Packet.py",
        "docs/PHASE22_STEP52_PHASE20_NETWORK_TRANSPORT_PLANNING_CLOSURE_DEFERRAL_RESOLUTION_DISPOSITION_HANDOFF_ACCEPTANCE_EVIDENCE_REVIEW_ALIGNMENT_PACKET.md",
        "tests/test_phase22_phase20_network_transport_planning_closure_deferral_resolution_disposition_handoff_acceptance_evidence_review_alignment_packet.py",
    ]:
        assert rel in text


def test_phase22_step52_expected_smoke_text_is_present():
    text = read(SCRIPT)
    assert "SMOKE TEST PASS: Phase 22 Step 52 Phase 20 Network Transport Planning Closure Deferral Resolution Disposition Handoff Acceptance Evidence Review Alignment Packet is present and planning-only." in text


def test_phase22_step52_menu_labels_phase_and_step():
    text = read(SCRIPT)
    assert "Phase 22 Step 52 menu" in text
    assert "Smoke test Phase 22 Step 52" in text


def test_phase22_step52_packet_declares_not_started_states():
    text = read(SCRIPT)
    assert 'implementation_phase_start = "not_started"' in text
    assert 'applied_layer_release = "not_started"' in text


def test_phase22_step52_uses_step_158_ui_page():
    assert UI_PAGE.name.startswith("158_")
    assert "Acceptance_Evidence_Review_Alignment_Packet" in UI_PAGE.name


def test_phase22_step52_public_files_avoid_sensitive_values():
    public_text = "\n".join(read(path) for path in [SCRIPT, UI_PAGE, DOC])
    forbidden = [
        "RC_CLIENT_SECRET",
        "LACRM_API_KEY",
        "FRESHBOOKS_CLIENT_SECRET",
        "sk_live_",
        "xoxb-",
    ]
    for token in forbidden:
        assert token not in public_text


def test_phase22_step52_launcher_packet_prints_expected_checks():
    text = read(SCRIPT)
    for token in [
        "PASS: closure_deferral_resolution_disposition_handoff_acceptance_evidence_review=planned_only",
        "PASS: handoff_acceptance_evidence_review_record_creation=false",
        "PASS: handoff_acceptance_evidence_review_approval_creation=false",
        "PASS: handoff_acceptance_evidence_review_execution=false",
    ]:
        assert token in text


def test_phase22_step52_doc_expected_pytest_count_is_current():
    text = read(DOC)
    assert "`25 passed`" in text


def test_phase22_step52_test_file_uses_repo_relative_paths():
    text = read(TEST_FILE)
    assert "STEP_FILES" in text
    assert "Path(__file__).resolve().parents[1]" in text


def test_phase22_step52_launcher_has_no_regex_backslash_normalizer():
    text = read(SCRIPT)
    assert "-replace" not in text
    assert "Replace([string][char]92" in text


def test_phase22_step52_acceptance_review_stays_separate_from_approval():
    public_text = "\n".join(read(path).lower() for path in [SCRIPT, UI_PAGE, DOC])
    assert "approval only in a later authorized phase" in public_text
    assert "handoff_acceptance_evidence_review_approval_creation = $false" in read(SCRIPT)


def test_phase22_step52_packet_includes_step_metadata():
    text = read(SCRIPT)
    assert "step = 52" in text
    assert "phase = 22" in text
    assert "Phase 22 Step 51 - Phase 20 Network Transport Planning Closure Deferral Resolution Disposition Handoff Acceptance Evidence Alignment Packet" in text
