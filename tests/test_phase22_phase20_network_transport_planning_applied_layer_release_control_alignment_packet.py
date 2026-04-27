from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

STEP_SCRIPT = ROOT / "scripts" / "phase22_generate_phase20_network_transport_planning_applied_layer_release_control_alignment_packet.ps1"
STEP_UI = ROOT / "ui" / "pages" / "139_Phase20_Network_Transport_Planning_Applied_Layer_Release_Control_Alignment_Packet.py"
STEP_DOC = ROOT / "docs" / "PHASE22_STEP33_PHASE20_NETWORK_TRANSPORT_PLANNING_APPLIED_LAYER_RELEASE_CONTROL_ALIGNMENT_PACKET.md"
STEP_TEST = ROOT / "tests" / "test_phase22_phase20_network_transport_planning_applied_layer_release_control_alignment_packet.py"

STEP_FILES = [STEP_SCRIPT, STEP_UI, STEP_DOC, STEP_TEST]


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_phase22_step33_files_exist():
    missing = [str(path) for path in STEP_FILES if not path.exists()]
    assert not missing


def test_phase22_step33_document_labels_phase_and_step():
    text = read(STEP_DOC)
    assert "Phase 22 Step 33" in text
    assert "Applied Layer Release Control Alignment Packet" in text
    assert "planning-only" in text


def test_phase22_step33_launcher_supports_optimized_actions():
    text = read(STEP_SCRIPT)
    assert '[ValidateSet("menu", "status", "apply", "smoke", "packet", "all")]' in text
    assert "Optimized launcher actions" in text
    assert '-Action status, apply, smoke, packet, all' in text


def test_phase22_step33_launcher_is_path_safe_and_idempotent():
    text = read(STEP_SCRIPT)
    assert "Test-Path -LiteralPath" in text
    assert "Copy-Item -LiteralPath" in text
    assert "source and target are the same file" in text
    assert "Remove-ControlCharacters" in text


def test_phase22_step33_safety_flags_present():
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


def test_phase22_step33_no_forbidden_runtime_tokens():
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


def test_phase22_step33_packet_outputs_expected_checks():
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
        "PASS: applied_layer_release_control_runtime=false",
        "PASS: release_control_record_creation=false",
        "PASS: release_decision_record_creation=false",
        "PASS: release_evidence_snapshot_record_creation=false",
        "PASS: decision_auto_apply_runtime=false",
        "PASS: approval_gate_runtime=false",
        "PASS: policy_enforcement_runtime=false",
        "CHECK: applied_layer_release_control_stage=planning_alignment_only",
        "CHECK: immutable_audit_log_required=true",
        "CHECK: append_only_audit_event_policy_required=true",
        "CHECK: rollback_plan_required=true",
        "CHECK: post_release_validation_required=true",
        "CHECK: connector_writeback_release_scope_required=true",
        "CHECK: rollback_reference_required=true",
        "CHECK: source_bucket_alignment=raw_normalized_matched_approved_applied",
    ]
    for token in expected:
        assert token in text


def test_phase22_step33_source_bucket_alignment_preserved():
    combined = "\n".join(read(path) for path in STEP_FILES)
    assert "raw_normalized_matched_approved_applied" in combined
    assert "connector_first_operating_core" in combined
    assert "connector_package_not_separate_product" in combined


def test_phase22_step33_applied_layer_release_control_is_planning_only():
    combined = "\n".join(read(path) for path in STEP_FILES)
    assert "applied_layer_release_control_stage" in combined
    assert "planning_alignment_only" in combined
    assert "applied_layer_release_control_runtime" in combined
    assert "release_control_record_creation" in combined
    assert "release_decision_record_creation" in combined
    assert "release_evidence_snapshot_record_creation" in combined


def test_phase22_step33_audit_prerequisites_are_recorded():
    combined = "\n".join(read(path) for path in STEP_FILES)
    for token in [
        "immutable_audit_log_required",
        "append_only_audit_event_policy_required",
        "rollback_plan_required",
        "post_release_validation_required",
        "connector_writeback_release_scope_required",
        "rollback_reference_required",
        "tamper_evidence_policy",
        "retention_policy",
    ]:
        assert token in combined


def test_phase22_step33_ui_is_planning_page_only():
    text = read(STEP_UI)
    assert "st.set_page_config" in text
    assert "Planning-only packet" in text
    assert "does not start network transport" in text
    assert "does not mutate the platform DB" in text
    assert "does not create release-control records" in text


def test_phase22_step33_branch_and_prior_step_are_recorded():
    text = read(STEP_SCRIPT)
    assert "phase22-step33-phase20-network-transport-planning-applied-layer-release-control-alignment-packet" in text
    assert "Phase 22 Step 32 - Phase 20 Network Transport Planning Approval Audit Trail Alignment Packet" in text
