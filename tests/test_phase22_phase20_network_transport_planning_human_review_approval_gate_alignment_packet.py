from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

STEP_SCRIPT = ROOT / "scripts" / "phase22_generate_phase20_network_transport_planning_human_review_approval_gate_alignment_packet.ps1"
STEP_UI = ROOT / "ui" / "pages" / "137_Phase20_Network_Transport_Planning_Human_Review_Approval_Gate_Alignment_Packet.py"
STEP_DOC = ROOT / "docs" / "PHASE22_STEP31_PHASE20_NETWORK_TRANSPORT_PLANNING_HUMAN_REVIEW_APPROVAL_GATE_ALIGNMENT_PACKET.md"
STEP_TEST = ROOT / "tests" / "test_phase22_phase20_network_transport_planning_human_review_approval_gate_alignment_packet.py"

STEP_FILES = [STEP_SCRIPT, STEP_UI, STEP_DOC, STEP_TEST]


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_phase22_step31_files_exist():
    missing = [str(path) for path in STEP_FILES if not path.exists()]
    assert not missing


def test_phase22_step31_document_labels_phase_and_step():
    text = read(STEP_DOC)
    assert "Phase 22 Step 31" in text
    assert "Human Review Approval Gate Alignment Packet" in text
    assert "planning-only" in text


def test_phase22_step31_launcher_supports_optimized_actions():
    text = read(STEP_SCRIPT)
    assert '[ValidateSet("menu", "status", "apply", "smoke", "packet", "all")]' in text
    assert "Optimized launcher actions" in text
    assert '-Action status, apply, smoke, packet, all' in text


def test_phase22_step31_launcher_is_path_safe_and_idempotent():
    text = read(STEP_SCRIPT)
    assert "Test-Path -LiteralPath" in text
    assert "Copy-Item -LiteralPath" in text
    assert "source and target are the same file" in text
    assert "Remove-ControlCharacters" in text


def test_phase22_step31_safety_flags_present():
    combined = "\n".join(read(path) for path in STEP_FILES)
    required = [
        "planning_only",
        "no_platform_db_mutation",
        "no_bridge_mutation",
        "no_real_bridge_http_client",
        "no_network_transport_implementation",
        "no_bridge_post",
        "no_network_sockets",
        "no_execution_implementation",
        "lacrm_default_mode",
        "dry_run",
        "live_write_disabled",
        "live_write_unarmed",
    ]
    for token in required:
        assert token in combined


def test_phase22_step31_no_forbidden_runtime_tokens():
    combined = "\n".join(read(path).lower() for path in STEP_FILES)
    forbidden_parts = [
        ("planning", "_", "only", "=", "false"),
        ("lacrm", "_", "live", "_", "write", "=", "true"),
        ("live", "_", "write", "_", "disabled", "=", "false"),
        ("live", "_", "write", "_", "unarmed", "=", "false"),
        ("implementation", "_", "phase", "_", "start", "=", "true"),
        ("authorization", "_", "record", "_", "creation", "=", "true"),
        ("operator", "_", "signoff", "_", "creation", "=", "true"),
        ("operator", "_", "approval", "_", "creation", "=", "true"),
        ("final", "_", "approval", "_", "creation", "=", "true"),
        ("design", "_", "closure", "_", "record", "_", "creation", "=", "true"),
        ("requests", ".", "post"),
        ("urllib", ".", "request"),
        ("http", ".", "client"),
        ("socket", ".", "create", "_", "connection"),
        ("fast", "api", "("),
        ("uvicorn", ".", "run"),
    ]
    for parts in forbidden_parts:
        assert "".join(parts) not in combined


def test_phase22_step31_packet_outputs_expected_checks():
    text = read(STEP_SCRIPT)
    expected = [
        "PASS: planning_only=true",
        "PASS: no_real_bridge_http_client=true",
        "PASS: no_network_transport_implementation=true",
        "PASS: no_bridge_post=true",
        "PASS: no_network_sockets=true",
        "PASS: lacrm_default_mode=dry_run",
        "PASS: live_write_disabled=true",
        "PASS: live_write_unarmed=true",
        "PASS: recommendation_engine_runtime=false",
        "PASS: recommendation_writeback_runtime=false",
        "PASS: recommendation_decision_application=false",
        "PASS: human_review_approval_gate_runtime=false",
        "PASS: decision_auto_apply_runtime=false",
        "PASS: approval_gate_runtime=false",
        "PASS: policy_enforcement_runtime=false",
        "CHECK: human_review_approval_gate_stage=planning_alignment_only",
        "CHECK: manual_approval_required=true",
        "CHECK: operator_review_required=true",
        "CHECK: veto_reason_required=true",
        "CHECK: confidence_threshold_policy_required=true",
        "CHECK: audit_trail_required=true",
        "CHECK: source_bucket_alignment=raw_normalized_matched_approved_applied",
    ]
    for token in expected:
        assert token in text


def test_phase22_step31_source_bucket_alignment_preserved():
    combined = "\n".join(read(path) for path in STEP_FILES)
    assert "raw_normalized_matched_approved_applied" in combined
    assert "connector_first_operating_core" in combined
    assert "connector_package_not_separate_product" in combined


def test_phase22_step31_human_review_approval_gate_is_planning_only():
    combined = "\n".join(read(path) for path in STEP_FILES)
    assert "human_review_approval_gate_stage" in combined
    assert "planning_alignment_only" in combined
    assert "human_review_approval_gate_runtime" in combined
    assert "decision_auto_apply_runtime" in combined
    assert "policy_enforcement_runtime" in combined
    assert "manual_approval_required" in combined


def test_phase22_step31_governance_prerequisites_are_recorded():
    combined = "\n".join(read(path) for path in STEP_FILES)
    for token in [
        "confidence_threshold_policy_required",
        "operator_review_required",
        "veto_reason_required",
        "audit_trail_required",
        "approval_gate_catalog",
        "branch_override_policy",
    ]:
        assert token in combined


def test_phase22_step31_ui_is_planning_page_only():
    text = read(STEP_UI)
    assert "st.set_page_config" in text
    assert "Planning-only packet" in text
    assert "does not start network transport" in text
    assert "does not mutate the platform DB" in text
    assert "does not enforce or apply decisions" in text


def test_phase22_step31_branch_and_prior_step_are_recorded():
    text = read(STEP_SCRIPT)
    assert "phase22-step31-phase20-network-transport-planning-human-review-approval-gate-alignment-packet" in text
    assert "Phase 22 Step 30 - Phase 20 Network Transport Planning Decision Boundary Governance Alignment Packet" in text
