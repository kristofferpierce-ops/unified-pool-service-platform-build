from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

STEP_FILES = [
    ROOT / "scripts" / "phase22_generate_phase20_network_transport_planning_canonical_event_ledger_alignment_packet.ps1",
    ROOT / "ui" / "pages" / "130_Phase20_Network_Transport_Planning_Canonical_Event_Ledger_Alignment_Packet.py",
    ROOT / "docs" / "PHASE22_STEP24_PHASE20_NETWORK_TRANSPORT_PLANNING_CANONICAL_EVENT_LEDGER_ALIGNMENT_PACKET.md",
    ROOT / "tests" / "test_phase22_phase20_network_transport_planning_canonical_event_ledger_alignment_packet.py",
]

STEP_SCRIPT = STEP_FILES[0]
UI_PAGE = STEP_FILES[1]
DOC_FILE = STEP_FILES[2]


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_phase22_step24_files_exist() -> None:
    missing = [str(path) for path in STEP_FILES if not path.exists()]
    assert missing == []


def test_phase22_step24_doc_declares_canonical_event_ledger_alignment() -> None:
    text = read(DOC_FILE)
    required = [
        "Phase 22 Step 24",
        "canonical event ledger",
        "time-stamped event tied to a stable internal entity",
        "source_bucket_alignment=raw_normalized_matched_approved_applied",
        "canonical_event_ledger_alignment_mode=planning_entity_event_traceability_only",
        "canonical_event_ledger_writes=false",
        "event_ledger_alignment=canonical_time_stamped_entity_tied_events",
        "bridge_absorption_target=connector_package_not_separate_product",
    ]
    for token in required:
        assert token in text


def test_phase22_step24_doc_declares_planning_only_safety() -> None:
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


def test_phase22_step24_launcher_supports_optimized_actions() -> None:
    text = read(STEP_SCRIPT)
    assert "ValidateSet" in text
    assert "status" in text
    assert "apply" in text
    assert "smoke" in text
    assert "packet" in text
    assert "all" in text
    assert "Invoke-Action $Action" in text


def test_phase22_step24_launcher_is_path_safe_and_idempotent() -> None:
    text = read(STEP_SCRIPT)
    assert "Remove-ControlCharacters" in text
    assert "Test-Path -LiteralPath" in text
    assert "Copy-Item -LiteralPath" in text
    assert "source and target are the same file" in text
    assert "OrdinalIgnoreCase" in text


def test_phase22_step24_blocks_runtime_execution() -> None:
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


def test_phase22_step24_packet_output_contains_required_pass_and_check_lines() -> None:
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
        "PASS: operating_intelligence_runtime=false",
        "PASS: expected_actual_runtime=false",
        "CHECK: implementation_phase_start=not_started",
        "CHECK: operator_signoff_creation=false",
        "CHECK: operator_approval_creation=false",
        "CHECK: final_approval_creation=false",
        "CHECK: design_closure_record_creation=false",
        "CHECK: source_bucket_alignment=raw_normalized_matched_approved_applied",
        "CHECK: event_ledger_alignment=canonical_time_stamped_entity_tied_events",
        "CHECK: bridge_absorption_target=connector_package_not_separate_product",
        "CHECK: connector_first_operating_core=true",
        "CHECK: packet_json=",
    ]
    for token in required:
        assert token in text


def test_phase22_step24_ui_is_read_only_planning_page() -> None:
    text = read(UI_PAGE)
    assert "Phase 22 Step 24" in text
    assert "Read-only planning checkpoint" in text
    assert "planning_entity_event_traceability_only" in text
    assert "canonical_event_ledger" in text
    assert "event_ledger_alignment" in text
    assert "expected_vs_actual_engine" in text


def test_phase22_step24_no_approval_or_design_closure_creation() -> None:
    combined = "\n".join(read(path) for path in [STEP_SCRIPT, UI_PAGE, DOC_FILE])
    required_blocks = [
        "operator_signoff_creation=false",
        "operator_approval_creation=false",
        "final_approval_creation=false",
        "design_closure_record_creation=false",
    ]
    for token in required_blocks:
        assert token in combined


def test_phase22_step24_preserves_event_examples_for_future_planning() -> None:
    combined = "\n".join(read(path) for path in [STEP_SCRIPT, UI_PAGE, DOC_FILE])
    required_examples = [
        "source payload received",
        "candidate match created",
        "quote created",
        "service visit completed",
        "customer called",
        "invoice paid",
        "route travel completed",
    ]
    for token in required_examples:
        assert token in combined
