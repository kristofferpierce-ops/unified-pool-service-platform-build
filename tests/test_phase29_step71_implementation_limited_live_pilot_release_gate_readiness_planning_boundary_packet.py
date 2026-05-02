from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts/phase29_step71_implementation_limited_live_pilot_release_gate_readiness_planning_boundary_packet.ps1"
UI_PAGE = REPO / "ui/pages/927_Phase29_Step71_Implementation_Limited_Live_Pilot_Release_Gate_Readiness_Planning_Boundary_Packet.py"
DOC = REPO / "docs/PHASE29_STEP71_IMPLEMENTATION_LIMITED_LIVE_PILOT_RELEASE_GATE_READINESS_PLANNING_BOUNDARY_PACKET.md"
TEST = REPO / "tests/test_phase29_step71_implementation_limited_live_pilot_release_gate_readiness_planning_boundary_packet.py"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


def test_phase29_step71_files_exist():
    assert SCRIPT.exists()
    assert UI_PAGE.exists()
    assert DOC.exists()
    assert TEST.exists()


def test_phase29_step71_launcher_supports_optimized_actions():
    script = read(SCRIPT)
    assert 'ValidateSet("status", "apply", "smoke", "packet", "all")' in script
    assert "APPLY PASS: Phase 29 Step 71" in script
    assert "SMOKE TEST PASS: Phase 29 Step 71" in script


def test_phase29_step71_safety_markers_present():
    combined = read(SCRIPT) + read(DOC) + read(UI_PAGE)
    for marker in [
        "planning_only",
        "no_real_bridge_http_client",
        "no_network_transport_implementation",
        "no_bridge_post",
        "no_network_sockets",
        "phase29_execution_start",
        "phase29_implementation_start",
        "implementation_phase_start",
        "limited_live_pilot_start",
        "limited_live_pilot_execution_start",
        "live_user_access_start",
        "phase30_start",
        "phase30_boundary_creation",
        "no_live_user_access",
        "lacrm_default_mode",
        "live_write_disabled",
        "live_write_unarmed",
    ]:
        assert marker in combined


def test_phase29_step71_does_not_enable_runtime_or_phase30():
    operational_text = read(SCRIPT) + read(DOC) + read(UI_PAGE)
    forbidden_enabled = [
        ("phase30_start", "true"),
        ("phase30_boundary_creation", "true"),
        ("phase29_execution_start", "true"),
        ("phase29_implementation_start", "true"),
        ("implementation_phase_start", "true"),
        ("limited_live_pilot_start", "true"),
        ("limited_live_pilot_execution_start", "true"),
        ("live_user_access_start", "true"),
        ("network_transport_runtime_start", "true"),
        ("bridge_transport_runtime_start", "true"),
        ("no_network_transport_implementation", "false"),
        ("no_bridge_post", "false"),
        ("no_network_sockets", "false"),
        ("no_live_user_access", "false"),
        ("live_write_disabled", "false"),
        ("live_write_unarmed", "false"),
    ]
    for name, value in forbidden_enabled:
        marker = f"{name}={value}"
        assert marker not in operational_text


def test_phase29_step71_doc_declares_no_phase30_boundary():
    doc = read(DOC).lower()
    assert "phase30_start=false" in doc
    assert "phase30_boundary_creation=false" in doc
    assert "no_live_user_access=true" in doc
    assert "no_bridge_post=true" in doc or "no bridge post" in doc
    assert "no_network_sockets=true" in doc or "no network sockets" in doc


def test_phase29_step71_ui_is_reference_only():
    ui = read(UI_PAGE)
    assert "reference-only" in ui
    assert "Phase 29" in ui or "phase29" in ui
    assert "live LACRM writes" in ui


def test_phase29_step71_prior_step_is_recorded():
    combined = read(SCRIPT) + read(DOC) + read(UI_PAGE)
    assert "Phase 29 Step 70 - Phase 20 Network Transport Implementation Limited Live Pilot No-Write Dry Run Result Disposition Planning Final Boundary Confirmation Packet" in combined


def test_phase29_step71_uses_exact_four_step_files():
    script = read(SCRIPT)
    for rel in [
        "scripts/phase29_step71_implementation_limited_live_pilot_release_gate_readiness_planning_boundary_packet.ps1",
        "ui/pages/927_Phase29_Step71_Implementation_Limited_Live_Pilot_Release_Gate_Readiness_Planning_Boundary_Packet.py",
        "docs/PHASE29_STEP71_IMPLEMENTATION_LIMITED_LIVE_PILOT_RELEASE_GATE_READINESS_PLANNING_BOUNDARY_PACKET.md",
        "tests/test_phase29_step71_implementation_limited_live_pilot_release_gate_readiness_planning_boundary_packet.py",
    ]:
        assert rel in script

