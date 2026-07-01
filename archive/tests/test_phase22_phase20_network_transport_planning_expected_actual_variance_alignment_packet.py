from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

STEP_FILES = [
    ROOT / "scripts" / "phase22_generate_phase20_network_transport_planning_expected_actual_variance_alignment_packet.ps1",
    ROOT / "ui" / "pages" / "131_Phase20_Network_Transport_Planning_Expected_Actual_Variance_Alignment_Packet.py",
    ROOT / "docs" / "PHASE22_STEP25_PHASE20_NETWORK_TRANSPORT_PLANNING_EXPECTED_ACTUAL_VARIANCE_ALIGNMENT_PACKET.md",
    ROOT / "tests" / "test_phase22_phase20_network_transport_planning_expected_actual_variance_alignment_packet.py",
]

STEP_SCRIPT = STEP_FILES[0]
UI_PAGE = STEP_FILES[1]
DOC_FILE = STEP_FILES[2]


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_phase22_step25_files_exist() -> None:
    missing = [str(path) for path in STEP_FILES if not path.exists()]
    assert missing == []


def test_phase22_step25_doc_declares_expected_actual_alignment() -> None:
    text = read(DOC_FILE)
    required = [
        "Phase 22 Step 25",
        "expected actual variance alignment",
        "inputs, model version, expected output, actual output, variance, confidence score, driver attribution, and business result",
        "expected_actual_alignment_mode=planning_variance_traceability_only",
        "expected_actual_writes=false",
        "variance_analysis_runtime=false",
        "probability_update_runtime=false",
        "required_future_estimate_fields=model_version_input_snapshot_expected_actual_variance_business_result",
    ]
    for token in required:
        assert token in text


def test_phase22_step25_doc_declares_planning_only_safety() -> None:
    text = read(DOC_FILE)
    required = [
        "planning_only=true",
        "no_real_bridge_http_client=true",
        "no_network_transport_implementation=true",
        "no_bridge_post=true",
        "no_network_sockets=true",
        "lacrm_default_mode=dry_run",
        "live_write_disabled=true",
        "live_write_unarmed=true",
        "operating_intelligence_runtime=false",
        "expected_actual_runtime=false",
    ]
    for token in required:
        assert token in text


def test_phase22_step25_launcher_supports_optimized_actions() -> None:
    text = read(STEP_SCRIPT)
    assert "ValidateSet" in text
    assert "status" in text
    assert "apply" in text
    assert "smoke" in text
    assert "packet" in text
    assert "all" in text
    assert "Invoke-Action $Action" in text


def test_phase22_step25_launcher_is_path_safe_and_idempotent() -> None:
    text = read(STEP_SCRIPT)
    assert "Remove-ControlCharacters" in text
    assert "Test-Path -LiteralPath" in text
    assert "Copy-Item -LiteralPath" in text
    assert "source and target are the same file" in text
    assert "OrdinalIgnoreCase" in text


def test_phase22_step25_blocks_runtime_execution() -> None:
    combined = "\n".join(read(path) for path in [STEP_SCRIPT, UI_PAGE, DOC_FILE])
    forbidden_runtime_calls = [
        "requests.post(",
        "httpx.post(",
        "Invoke-WebRequest ",
        "Invoke-RestMethod ",
        "socket.socket(",
        "uvicorn.run(",
        "subprocess.run(",
    ]
    for token in forbidden_runtime_calls:
        assert token not in combined


def test_phase22_step25_packet_output_contains_required_pass_and_check_lines() -> None:
    text = read(STEP_SCRIPT)
    required = [
        "PASS: planning_only=true",
        "PASS: no_real_bridge_http_client=true",
        "PASS: no_network_transport_implementation=true",
        "PASS: no_bridge_post=true",
        "PASS: no_network_sockets=true",
        "PASS: lacrm_default_mode=dry_run",
        "PASS: live_write_disabled=true",
        "PASS: live_write_unarmed=true",
        "PASS: source_bucket_writes=false",
        "PASS: canonical_event_ledger_writes=false",
        "PASS: expected_actual_writes=false",
        "PASS: expected_actual_runtime=false",
        "PASS: variance_analysis_runtime=false",
        "PASS: probability_update_runtime=false",
        "PASS: operating_intelligence_runtime=false",
        "CHECK: implementation_phase_start=not_started",
        "CHECK: operator_signoff_creation=false",
        "CHECK: operator_approval_creation=false",
        "CHECK: final_approval_creation=false",
        "CHECK: design_closure_record_creation=false",
        "CHECK: source_bucket_alignment=raw_normalized_matched_approved_applied",
        "CHECK: event_ledger_dependency=time_stamped_entity_tied_events",
        "CHECK: expected_actual_alignment=variance_confidence_driver_attribution",
        "CHECK: required_future_estimate_fields=model_version_input_snapshot_expected_actual_variance_business_result",
        "CHECK: bridge_absorption_target=connector_package_not_separate_product",
        "CHECK: connector_first_operating_core=true",
        "CHECK: packet_json=",
    ]
    for token in required:
        assert token in text


def test_phase22_step25_ui_is_read_only_planning_page() -> None:
    text = read(UI_PAGE)
    assert "Phase 22 Step 25" in text
    assert "Read-only planning checkpoint" in text
    assert "planning_variance_traceability_only" in text
    assert "expected_actual_alignment" in text
    assert "variance_confidence_driver_attribution" in text
    assert "chemical_usage" in text
    assert "route_profitability" in text


def test_phase22_step25_no_approval_or_design_closure_creation() -> None:
    combined = "\n".join(read(path) for path in [STEP_SCRIPT, UI_PAGE, DOC_FILE])
    required_blocks = [
        "operator_signoff_creation=false",
        "operator_approval_creation=false",
        "final_approval_creation=false",
        "design_closure_record_creation=false",
    ]
    for token in required_blocks:
        assert token in combined


def test_phase22_step25_preserves_future_driver_models_for_planning() -> None:
    combined = "\n".join(read(path) for path in [STEP_SCRIPT, UI_PAGE, DOC_FILE])
    required_examples = [
        "climate_baseline",
        "chemical_usage_baseline",
        "labor_baseline",
        "overhead_baseline",
        "branch_prior",
        "seasonal_prior",
        "tech_prior",
        "account_class_prior",
    ]
    for token in required_examples:
        assert token in combined


def test_phase22_step25_preserves_future_estimate_fields_for_planning() -> None:
    combined = "\n".join(read(path) for path in [STEP_SCRIPT, UI_PAGE, DOC_FILE])
    required_fields = [
        "model_version",
        "input_snapshot",
        "expected_output",
        "actual_output",
        "variance",
        "confidence_score",
        "driver_attribution",
        "business_result",
    ]
    for token in required_fields:
        assert token in combined
