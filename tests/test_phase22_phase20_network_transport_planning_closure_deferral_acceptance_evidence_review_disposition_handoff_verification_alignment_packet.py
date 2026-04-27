from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

SCRIPT = ROOT / "scripts/phase22_generate_phase20_network_transport_planning_closure_deferral_acceptance_evidence_review_disposition_handoff_verification_alignment.ps1"
PAGE = ROOT / "ui/pages/161_Phase20_Network_Transport_Planning_Closure_Deferral_Acceptance_Evidence_Review_Disposition_Handoff_Verification_Alignment_Packet.py"
DOC = ROOT / "docs/PHASE22_STEP55_PHASE20_NETWORK_TRANSPORT_PLANNING_CLOSURE_DEFERRAL_ACCEPTANCE_EVIDENCE_REVIEW_DISPOSITION_HANDOFF_VERIFICATION_ALIGNMENT_PACKET.md"
TEST_FILE = ROOT / "tests/test_phase22_phase20_network_transport_planning_closure_deferral_acceptance_evidence_review_disposition_handoff_verification_alignment_packet.py"

STEP_FILES = [SCRIPT, PAGE, DOC, TEST_FILE]


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def combined_public_text() -> str:
    return "\n".join(read(path) for path in [SCRIPT, PAGE, DOC])


def test_step55_files_exist():
    for path in STEP_FILES:
        assert path.exists(), path


def test_step55_script_declares_phase_and_step():
    text = read(SCRIPT)
    assert "Phase 22 Step 55" in text
    assert "Phase 20 Network Transport Planning Closure Deferral Acceptance Evidence Review Disposition Handoff Verification Alignment Packet" in text


def test_step55_expected_branch_is_declared():
    assert "phase22-step55-phase20-network-transport-planning-closure-deferral-acceptance-evidence-review-disposition-handoff-verification-alignment-packet" in read(SCRIPT)


def test_step55_prior_step_is_declared():
    assert "Phase 22 Step 54 - Phase 20 Network Transport Planning Closure Deferral Acceptance Evidence Review Disposition Handoff Alignment Packet" in read(SCRIPT)


def test_step55_launcher_supports_action_all():
    text = read(SCRIPT)
    assert "ValidateSet(\"menu\", \"status\", \"apply\", \"smoke\", \"packet\", \"all\")" in text
    assert "\"all\"" in text


def test_step55_launcher_has_parent_workspace_safe_repo_root():
    text = read(SCRIPT)
    assert "Resolve-RepoRoot" in text
    assert "Pass -RepoRoot explicitly" in text


def test_step55_launcher_uses_literal_paths():
    text = read(SCRIPT)
    assert "Test-Path -LiteralPath" in text
    assert "Set-Content -LiteralPath" in text


def test_step55_launcher_uses_safe_path_joining_without_regex():
    text = read(SCRIPT)
    assert "Join-SafePath" in text
    assert ".Replace(\"/\", \"\\\")" in text
    assert "-replace" not in text


def test_step55_step_files_are_declared():
    text = read(SCRIPT)
    for rel in [
        "scripts/phase22_generate_phase20_network_transport_planning_closure_deferral_acceptance_evidence_review_disposition_handoff_verification_alignment.ps1",
        "ui/pages/161_Phase20_Network_Transport_Planning_Closure_Deferral_Acceptance_Evidence_Review_Disposition_Handoff_Verification_Alignment_Packet.py",
        "docs/PHASE22_STEP55_PHASE20_NETWORK_TRANSPORT_PLANNING_CLOSURE_DEFERRAL_ACCEPTANCE_EVIDENCE_REVIEW_DISPOSITION_HANDOFF_VERIFICATION_ALIGNMENT_PACKET.md",
        "tests/test_phase22_phase20_network_transport_planning_closure_deferral_acceptance_evidence_review_disposition_handoff_verification_alignment_packet.py",
    ]:
        assert rel in text


def test_step55_page_number_is_correct():
    assert "ui/pages/161_Phase20_Network_Transport_Planning_Closure_Deferral_Acceptance_Evidence_Review_Disposition_Handoff_Verification_Alignment_Packet.py" in PAGE.as_posix()


def test_step55_page_title_is_correct():
    text = read(PAGE)
    assert "Phase 22 Step 55" in text
    assert "Closure Deferral Acceptance Evidence Review Disposition Handoff Verification Alignment" in text


def test_step55_doc_title_is_correct():
    text = read(DOC)
    assert "# Phase 22 Step 55 - Phase 20 Network Transport Planning Closure Deferral Acceptance Evidence Review Disposition Handoff Verification Alignment Packet" in text


def test_step55_doc_lists_all_step_files():
    text = read(DOC)
    for rel in [
        "scripts/phase22_generate_phase20_network_transport_planning_closure_deferral_acceptance_evidence_review_disposition_handoff_verification_alignment.ps1",
        "ui/pages/161_Phase20_Network_Transport_Planning_Closure_Deferral_Acceptance_Evidence_Review_Disposition_Handoff_Verification_Alignment_Packet.py",
        "docs/PHASE22_STEP55_PHASE20_NETWORK_TRANSPORT_PLANNING_CLOSURE_DEFERRAL_ACCEPTANCE_EVIDENCE_REVIEW_DISPOSITION_HANDOFF_VERIFICATION_ALIGNMENT_PACKET.md",
        "tests/test_phase22_phase20_network_transport_planning_closure_deferral_acceptance_evidence_review_disposition_handoff_verification_alignment_packet.py",
    ]:
        assert rel in text


def test_step55_planning_only_is_declared():
    assert "planning_only" in combined_public_text()
    assert "planning-only" in combined_public_text()


def test_step55_no_platform_db_mutation_guard_exists():
    assert "no_platform_db_mutation" in combined_public_text()


def test_step55_no_bridge_mutation_guard_exists():
    assert "no_bridge_mutation" in combined_public_text()


def test_step55_no_real_bridge_http_client_guard_exists():
    assert "no_real_bridge_http_client" in combined_public_text()


def test_step55_no_network_transport_guard_exists():
    assert "no_network_transport_implementation" in combined_public_text()


def test_step55_no_bridge_post_guard_exists():
    assert "no_bridge_post" in combined_public_text()


def test_step55_no_network_sockets_guard_exists():
    assert "no_network_sockets" in combined_public_text()


def test_step55_lacrm_dry_run_guard_exists():
    text = combined_public_text()
    assert "lacrm_default_mode" in text
    assert "dry_run" in text


def test_step55_live_write_guards_exist():
    text = combined_public_text()
    assert "live_write_disabled" in text
    assert "live_write_unarmed" in text


def test_step55_handoff_verification_guards_exist():
    text = combined_public_text()
    assert "handoff_verification_record_creation" in text
    assert "handoff_verification_queue_creation" in text
    assert "handoff_verification_acceptance_creation" in text
    assert "handoff_verification_execution" in text


def test_step55_handoff_verification_is_planned_only():
    text = combined_public_text()
    assert "handoff_acceptance_evidence_review_disposition_handoff_verification" in text
    assert "planned_only" in text


def test_step55_does_not_create_approvals_or_closure_records():
    text = combined_public_text()
    forbidden = [
        "operator_signoff_creation = $true",
        "operator_approval_creation = $true",
        "final_approval_creation = $true",
        "        design_closure_record_creation = $true",
        "closure_decision_creation = $true",
        "handoff_verification_record_creation = $true",
        "handoff_verification_queue_creation = $true",
        "handoff_verification_acceptance_creation = $true",
    ]
    for marker in forbidden:
        assert marker not in text


def test_step55_packet_generation_is_json_only():
    text = read(SCRIPT)
    assert "ConvertTo-Json" in text
    assert "phase22_step55_handoff_verification_packet.json" in text


def test_step55_expected_smoke_text_exists():
    assert "SMOKE TEST PASS: Phase 22 Step 55 Phase 20 Network Transport Planning Closure Deferral Acceptance Evidence Review Disposition Handoff Verification Alignment Packet is present and planning-only." in read(SCRIPT)


def test_step55_public_files_are_utf8_readable():
    for path in STEP_FILES:
        assert read(path)


def test_step55_no_double_dash_text_in_public_docs():
    for path in [PAGE, DOC]:
        assert "--" not in read(path)


def test_step55_pytest_count_anchor():
    test_functions = [
        line
        for line in read(TEST_FILE).splitlines()
        if line.startswith("def test_")
    ]
    assert len(test_functions) == 30

