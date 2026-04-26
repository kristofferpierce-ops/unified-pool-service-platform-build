from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

STEP_FILES = [
    ROOT / "scripts" / "phase22_generate_phase20_network_transport_planning_driver_attribution_alignment_packet.ps1",
    ROOT / "ui" / "pages" / "132_Phase20_Network_Transport_Planning_Driver_Attribution_Alignment_Packet.py",
    ROOT / "docs" / "PHASE22_STEP26_PHASE20_NETWORK_TRANSPORT_PLANNING_DRIVER_ATTRIBUTION_ALIGNMENT_PACKET.md",
    ROOT / "tests" / "test_phase22_phase20_network_transport_planning_driver_attribution_alignment_packet.py",
]

STEP_SCRIPT = STEP_FILES[0]
UI_PAGE = STEP_FILES[1]
DOC_FILE = STEP_FILES[2]


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_phase22_step26_files_exist() -> None:
    assert [str(path) for path in STEP_FILES if not path.exists()] == []


def test_phase22_step26_doc_declares_driver_attribution_alignment() -> None:
    text = read(DOC_FILE)
    for token in [
        "Phase 22 Step 26",
        "driver attribution alignment",
        "planning_driver_traceability_only",
        "driver_attribution_writes=false",
        "driver_attribution_runtime=false",
        "driver_attribution_engine_runtime=false",
        "candidate_drivers_evidence_confidence_operator_review",
    ]:
        assert token in text


def test_phase22_step26_doc_declares_planning_only_safety() -> None:
    text = read(DOC_FILE)
    for token in [
        "planning_only=true",
        "no_real_bridge_http_client=true",
        "no_network_transport_implementation=true",
        "no_bridge_post=true",
        "no_network_sockets=true",
        "lacrm_default_mode=dry_run",
        "live_write_disabled=true",
        "live_write_unarmed=true",
        "operating_intelligence_runtime=false",
    ]:
        assert token in text


def test_phase22_step26_launcher_supports_optimized_actions() -> None:
    text = read(STEP_SCRIPT)
    assert "ValidateSet" in text
    for token in ["status", "apply", "smoke", "packet", "all", "Invoke-Action $Action"]:
        assert token in text


def test_phase22_step26_launcher_is_path_safe_and_idempotent() -> None:
    text = read(STEP_SCRIPT)
    for token in ["Remove-ControlCharacters", "Test-Path -LiteralPath", "Copy-Item -LiteralPath", "source and target are the same file", "OrdinalIgnoreCase"]:
        assert token in text


def test_phase22_step26_blocks_runtime_execution() -> None:
    combined = "\n".join(read(path) for path in [STEP_SCRIPT, UI_PAGE, DOC_FILE])
    for token in ["requests.post(", "httpx.post(", "Invoke-WebRequest ", "Invoke-RestMethod ", "socket.socket(", "uvicorn.run(", "subprocess.run("]:
        assert token not in combined


def test_phase22_step26_packet_output_contains_required_pass_and_check_lines() -> None:
    text = read(STEP_SCRIPT)
    for token in [
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
        "PASS: variance_analysis_runtime=false",
        "PASS: driver_attribution_writes=false",
        "PASS: driver_attribution_runtime=false",
        "PASS: driver_attribution_engine_runtime=false",
        "PASS: probability_update_runtime=false",
        "PASS: recommendation_engine_runtime=false",
        "PASS: operating_intelligence_runtime=false",
        "CHECK: implementation_phase_start=not_started",
        "CHECK: source_bucket_alignment=raw_normalized_matched_approved_applied",
        "CHECK: event_ledger_dependency=time_stamped_entity_tied_events",
        "CHECK: expected_actual_dependency=variance_records_before_driver_attribution",
        "CHECK: driver_attribution_alignment=candidate_drivers_evidence_confidence_operator_review",
        "CHECK: reserved_driver_groups=climate_chemical_labor_route_equipment_water_billing_customer_vendor_branch",
        "CHECK: connector_first_operating_core=true",
        "CHECK: packet_json=",
    ]:
        assert token in text


def test_phase22_step26_ui_is_read_only_planning_page() -> None:
    text = read(UI_PAGE)
    for token in ["Phase 22 Step 26", "Read-only planning checkpoint", "planning_driver_traceability_only", "driver_attribution_alignment", "climate_driver", "branch_overlay_driver"]:
        assert token in text


def test_phase22_step26_no_approval_or_design_closure_creation() -> None:
    combined = "\n".join(read(path) for path in [STEP_SCRIPT, UI_PAGE, DOC_FILE])
    for token in ["operator_signoff_creation=false", "operator_approval_creation=false", "final_approval_creation=false", "design_closure_record_creation=false"]:
        assert token in combined


def test_phase22_step26_preserves_candidate_driver_groups_for_planning() -> None:
    combined = "\n".join(read(path) for path in [STEP_SCRIPT, UI_PAGE, DOC_FILE])
    for token in ["climate_driver", "chemical_driver", "labor_driver", "route_driver", "equipment_driver", "water_source_driver", "billing_driver", "customer_behavior_driver", "vendor_cost_driver", "branch_overlay_driver"]:
        assert token in combined


def test_phase22_step26_preserves_attribution_record_shape_for_planning() -> None:
    combined = "\n".join(read(path) for path in [STEP_SCRIPT, UI_PAGE, DOC_FILE])
    for token in ["variance_id", "candidate_driver", "driver_weight", "confidence_score", "evidence_snapshot", "operator_review_status", "business_result"]:
        assert token in combined
