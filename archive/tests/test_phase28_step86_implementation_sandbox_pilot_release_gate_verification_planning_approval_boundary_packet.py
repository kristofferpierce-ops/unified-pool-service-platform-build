from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/phase28_step86_implementation_sandbox_pilot_release_gate_verification_planning_approval_boundary_packet.ps1"
UI = ROOT / "ui/pages/822_Phase28_Step86_Implementation_Sandbox_Pilot_Release_Gate_Verification_Planning_Approval_Boundary_Packet.py"
DOC = ROOT / "docs/PHASE28_STEP86_IMPLEMENTATION_SANDBOX_PILOT_RELEASE_GATE_VERIFICATION_PLANNING_APPROVAL_BOUNDARY_PACKET.md"
TEST = ROOT / "tests/test_phase28_step86_implementation_sandbox_pilot_release_gate_verification_planning_approval_boundary_packet.py"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


def test_phase28_step86_files_exist():
    assert SCRIPT.exists()
    assert UI.exists()
    assert DOC.exists()
    assert TEST.exists()


def test_phase28_step86_launcher_supports_optimized_actions():
    script = read(SCRIPT)
    assert 'ValidateSet("status", "apply", "smoke", "packet", "all")' in script
    assert "APPLY PASS: Phase 28 Step 86" in script
    assert "SMOKE TEST PASS: Phase 28 Step 86" in script


def test_phase28_step86_safety_markers_in_launcher():
    script = read(SCRIPT)
    required = [
        "planning_only",
        "no_real_bridge_http_client",
        "no_network_transport_implementation",
        "no_bridge_post",
        "no_network_sockets",
        "phase28_execution_start",
        "phase28_implementation_start",
        "implementation_phase_start",
        "sandbox_pilot_start",
        "sandbox_pilot_execution_start",
        "phase29_start",
        "phase29_boundary_creation",
        "live_write_disabled",
        "live_write_unarmed",
    ]
    for marker in required:
        assert marker in script


def test_phase28_step86_ui_is_reference_only():
    ui = read(UI)
    assert "Planning-only packet" in ui
    assert "no_network_transport_implementation=true" in ui
    assert "phase29_start=false" in ui
    assert "reference-only" in ui


def test_phase28_step86_doc_records_boundary_and_prior_step():
    doc = read(DOC)
    assert "Phase 28 Step 86" in doc
    assert "implementation_sandbox_pilot_release_gate_verification_planning_approval_boundary_opened_by_packet" in doc
    assert "Phase 28 Step 85 - Phase 20 Network Transport Implementation Sandbox Pilot Release Gate Verification Planning Safety Disposition Review Packet" in doc
    assert "phase29_boundary_creation=false" in doc


def test_phase28_step86_operational_files_do_not_enable_forbidden_markers():
    operational = read(SCRIPT) + "\n" + read(UI) + "\n" + read(DOC)
    forbidden = [
        "phase29_start=" + "true",
        "phase29_boundary_creation=" + "true",
        "phase28_execution_start=" + "true",
        "phase28_implementation_start=" + "true",
        "implementation_phase_start=" + "true",
        "sandbox_pilot_start=" + "true",
        "sandbox_pilot_execution_start=" + "true",
        "network_transport_runtime_start=" + "true",
        "bridge_transport_runtime_start=" + "true",
        "no_network_transport_implementation=" + "false",
        "no_bridge_post=" + "false",
        "no_network_sockets=" + "false",
        "live_write_disabled=" + "false",
        "live_write_unarmed=" + "false",
    ]
    lowered = operational.lower()
    for phrase in forbidden:
        assert phrase not in lowered


def test_phase28_step86_exact_step_identity():
    script = read(SCRIPT)
    doc = read(DOC)
    assert "Phase 28 Step 86 - Phase 20 Network Transport Implementation Sandbox Pilot Release Gate Verification Planning Approval Boundary Packet" in script
    assert "Phase 28 Step 86 - Phase 20 Network Transport Implementation Sandbox Pilot Release Gate Verification Planning Approval Boundary Packet" in doc
    assert "phase28-step86-implementation-sandbox-pilot-release-gate-verification-planning-approval-boundary" in script


def test_phase28_step86_four_file_staging_targets_are_documented():
    doc = read(DOC)
    assert "scripts/phase28_step86_implementation_sandbox_pilot_release_gate_verification_planning_approval_boundary_packet.ps1" in doc
    assert "ui/pages/822_Phase28_Step86_Implementation_Sandbox_Pilot_Release_Gate_Verification_Planning_Approval_Boundary_Packet.py" in doc
    assert "docs/PHASE28_STEP86_IMPLEMENTATION_SANDBOX_PILOT_RELEASE_GATE_VERIFICATION_PLANNING_APPROVAL_BOUNDARY_PACKET.md" in doc
    assert "tests/test_phase28_step86_implementation_sandbox_pilot_release_gate_verification_planning_approval_boundary_packet.py" in doc

