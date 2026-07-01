from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

STEP_FILES = [
    ROOT / "scripts/phase22_generate_phase20_network_transport_planning_closure_deferral_resolution_disposition_handoff_acceptance_evidence_alignment_packet.ps1",
    ROOT / "ui/pages/157_Phase20_Network_Transport_Planning_Closure_Deferral_Resolution_Disposition_Handoff_Acceptance_Evidence_Alignment_Packet.py",
    ROOT / "docs/PHASE22_STEP51_PHASE20_NETWORK_TRANSPORT_PLANNING_CLOSURE_DEFERRAL_RESOLUTION_DISPOSITION_HANDOFF_ACCEPTANCE_EVIDENCE_ALIGNMENT_PACKET.md",
    ROOT / "tests/test_phase22_phase20_network_transport_planning_closure_deferral_resolution_disposition_handoff_acceptance_evidence_alignment_packet.py",
]

SCRIPT = STEP_FILES[0]
UI_PAGE = STEP_FILES[1]
DOC = STEP_FILES[2]
TEST_FILE = STEP_FILES[3]


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_phase22_step51_files_exist():
    for path in STEP_FILES:
        assert path.exists(), f"missing {path}"


def test_phase22_step51_script_has_expected_title_and_branch():
    text = read(SCRIPT)
    assert "Phase 22 Step 51 - Phase 20 Network Transport Planning Closure Deferral Resolution Disposition Handoff Acceptance Evidence Alignment Packet" in text
    assert "phase22-step51-phase20-network-transport-planning-closure-deferral-resolution-disposition-handoff-acceptance-evidence-alignment-packet" in text


def test_phase22_step51_launcher_supports_optimized_actions():
    text = read(SCRIPT)
    for token in ["status", "apply", "smoke", "packet", "server", "all", "menu"]:
        assert token in text


def test_phase22_step51_launcher_is_path_safe():
    text = read(SCRIPT)
    assert "Test-Path -LiteralPath" in text
    assert "Set-Content -LiteralPath" in text
    assert "Get-Content -LiteralPath" in text
    assert "Join-RepoPath" in text
    assert "Normalize-RelativePath" in text


def test_phase22_step51_launcher_is_planning_only():
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


def test_phase22_step51_lacrm_guardrails_are_dry_run_only():
    text = read(SCRIPT)
    assert 'lacrm_default_mode = "dry_run"' in text
    assert "lacrm_live_write = $false" in text
    assert "live_write_disabled = $true" in text
    assert "live_write_unarmed = $true" in text


def test_phase22_step51_acceptance_evidence_does_not_create_records():
    text = read(SCRIPT)
    for token in [
        "handoff_acceptance_evidence_record_creation = $false",
        "handoff_acceptance_evidence_approval_creation = $false",
        "handoff_acceptance_evidence_execution = $false",
        "handoff_acceptance_gate_creation = $false",
        "handoff_acceptance_execution = $false",
        "closure_decision_creation = $false",
        "handoff_queue_creation = $false",
    ]:
        assert token in text


def test_phase22_step51_packet_generation_is_backup_only():
    text = read(SCRIPT)
    assert 'Join-Path $ResolvedRepoRoot "backups"' in text
    assert "ConvertTo-Json" in text
    assert "phase22_phase20_network_transport_planning_closure_deferral_resolution_disposition_handoff_acceptance_evidence_alignment_packet.json" in text


def test_phase22_step51_no_runtime_network_tokens_in_public_files():
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


def test_phase22_step51_doc_declares_no_write_scope():
    text = read(DOC)
    for phrase in [
        "No platform database mutation",
        "No bridge database mutation",
        "No real bridge HTTP client",
        "No handoff acceptance evidence record creation",
        "No handoff acceptance execution",
        "LACRM default mode remains `dry_run`",
    ]:
        assert phrase in text


def test_phase22_step51_ui_is_planning_only():
    text = read(UI_PAGE)
    assert "Planning-only" in text
    assert '"planning_only": True' in text
    assert '"handoff_acceptance_evidence_record_creation": False' in text
    assert '"handoff_acceptance_evidence_execution": False' in text
    assert '"lacrm_default_mode": "dry_run"' in text


def test_phase22_step51_ui_has_operator_context():
    text = read(UI_PAGE)
    assert "Operator note" in text
    assert "acceptance-evidence criteria" in text or "acceptance-evidence alignment" in text


def test_phase22_step51_source_bucket_alignment_preserved():
    text = read(DOC) + read(SCRIPT)
    assert "raw to normalized to matched to approved to applied" in text.lower()
    assert "connector_package_not_separate_product" in text


def test_phase22_step51_expected_step_files_are_referenced_by_launcher():
    text = read(SCRIPT)
    for rel in [
        "scripts/phase22_generate_phase20_network_transport_planning_closure_deferral_resolution_disposition_handoff_acceptance_evidence_alignment_packet.ps1",
        "ui/pages/157_Phase20_Network_Transport_Planning_Closure_Deferral_Resolution_Disposition_Handoff_Acceptance_Evidence_Alignment_Packet.py",
        "docs/PHASE22_STEP51_PHASE20_NETWORK_TRANSPORT_PLANNING_CLOSURE_DEFERRAL_RESOLUTION_DISPOSITION_HANDOFF_ACCEPTANCE_EVIDENCE_ALIGNMENT_PACKET.md",
        "tests/test_phase22_phase20_network_transport_planning_closure_deferral_resolution_disposition_handoff_acceptance_evidence_alignment_packet.py",
    ]:
        assert rel in text


def test_phase22_step51_expected_smoke_text_is_present():
    text = read(SCRIPT)
    assert "SMOKE TEST PASS: Phase 22 Step 51 Phase 20 Network Transport Planning Closure Deferral Resolution Disposition Handoff Acceptance Evidence Alignment Packet is present and planning-only." in text


def test_phase22_step51_menu_labels_phase_and_step():
    text = read(SCRIPT)
    assert "Phase 22 Step 51 menu" in text
    assert "Smoke test Phase 22 Step 51" in text


def test_phase22_step51_no_approval_or_closure_execution_language():
    public_text = "\n".join(read(path).lower() for path in [SCRIPT, UI_PAGE, DOC])
    forbidden = [
        "create closure decision",
        "approve closure",
        "finalize closure",
        "start implementation",
        "execute handoff acceptance",
        "create acceptance evidence record",
    ]
    for token in forbidden:
        assert token not in public_text


def test_phase22_step51_packet_declares_not_started_states():
    text = read(SCRIPT)
    assert 'implementation_phase_start = "not_started"' in text
    assert 'applied_layer_release = "not_started"' in text


def test_phase22_step51_uses_step_157_ui_page():
    assert UI_PAGE.name.startswith("157_")
    assert "Acceptance_Evidence_Alignment_Packet" in UI_PAGE.name


def test_phase22_step51_tests_cover_installer_safe_relative_paths():
    text = read(TEST_FILE)
    assert "STEP_FILES" in text
    assert "Path(__file__).resolve().parents[1]" in text


def test_phase22_step51_public_files_avoid_sensitive_values():
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


def test_phase22_step51_launcher_packet_prints_expected_checks():
    text = read(SCRIPT)
    for token in [
        "PASS: closure_deferral_resolution_disposition_handoff_acceptance_evidence=planned_only",
        "PASS: handoff_acceptance_evidence_record_creation=false",
        "PASS: handoff_acceptance_evidence_approval_creation=false",
        "PASS: handoff_acceptance_evidence_execution=false",
    ]:
        assert token in text


def test_phase22_step51_doc_expected_pytest_count_is_current():
    text = read(DOC)
    assert "`23 passed`" in text
