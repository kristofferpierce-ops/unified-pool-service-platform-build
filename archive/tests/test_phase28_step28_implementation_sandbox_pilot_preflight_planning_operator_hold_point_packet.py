from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts/phase28_step28_implementation_sandbox_pilot_preflight_planning_operator_hold_point_packet.ps1"
UI_PAGE = REPO / "ui/pages/764_Phase28_Step28_Implementation_Sandbox_Pilot_Preflight_Planning_Operator_Hold_Point_Packet.py"
DOC = REPO / "docs/PHASE28_STEP28_IMPLEMENTATION_SANDBOX_PILOT_PREFLIGHT_PLANNING_OPERATOR_HOLD_POINT_PACKET.md"
TEST = REPO / "tests/test_phase28_step28_implementation_sandbox_pilot_preflight_planning_operator_hold_point_packet.py"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


def test_phase28_step28_files_exist():
    assert SCRIPT.exists()
    assert UI_PAGE.exists()
    assert DOC.exists()
    assert TEST.exists()


def test_phase28_step28_launcher_supports_optimized_actions():
    script = read(SCRIPT)
    assert 'ValidateSet("status", "apply", "smoke", "packet", "all")' in script
    assert "APPLY PASS: Phase 28 Step 28" in script
    assert "SMOKE TEST PASS: Phase 28 Step 28" in script


def test_phase28_step28_safety_markers_present():
    combined = read(SCRIPT) + read(DOC) + read(UI_PAGE)
    for marker in [
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
        "lacrm_default_mode",
        "live_write_disabled",
        "live_write_unarmed",
    ]:
        assert marker in combined


def test_phase28_step28_does_not_enable_runtime_or_phase29():
    operational_text = read(SCRIPT) + read(DOC) + read(UI_PAGE)
    forbidden_enabled = [
        ("phase29_start", "true"),
        ("phase29_boundary_creation", "true"),
        ("phase28_execution_start", "true"),
        ("phase28_implementation_start", "true"),
        ("implementation_phase_start", "true"),
        ("sandbox_pilot_start", "true"),
        ("sandbox_pilot_execution_start", "true"),
        ("network_transport_runtime_start", "true"),
        ("bridge_transport_runtime_start", "true"),
        ("no_network_transport_implementation", "false"),
        ("no_bridge_post", "false"),
        ("no_network_sockets", "false"),
        ("live_write_disabled", "false"),
        ("live_write_unarmed", "false"),
    ]
    for name, value in forbidden_enabled:
        marker = f"{name}={value}"
        assert marker not in operational_text


def test_phase28_step28_doc_declares_no_phase29_boundary():
    doc = read(DOC).lower()
    assert "phase29_start=false" in doc
    assert "phase29_boundary_creation=false" in doc
    assert "no_bridge_post=true" in doc or "no bridge post" in doc
    assert "no_network_sockets=true" in doc or "no network sockets" in doc


def test_phase28_step28_ui_is_reference_only():
    ui = read(UI_PAGE)
    assert "reference-only" in ui
    assert "Phase 29" in ui or "phase29" in ui
    assert "live LACRM writes" in ui


def test_phase28_step28_prior_step_is_recorded():
    combined = read(SCRIPT) + read(DOC) + read(UI_PAGE)
    assert "Phase 28 Step 27 - Phase 20 Network Transport Implementation Sandbox Pilot Preflight Planning Approval Readiness Packet" in combined


def test_phase28_step28_uses_exact_four_step_files():
    script = read(SCRIPT)
    for rel in [
        "scripts/phase28_step28_implementation_sandbox_pilot_preflight_planning_operator_hold_point_packet.ps1",
        "ui/pages/764_Phase28_Step28_Implementation_Sandbox_Pilot_Preflight_Planning_Operator_Hold_Point_Packet.py",
        "docs/PHASE28_STEP28_IMPLEMENTATION_SANDBOX_PILOT_PREFLIGHT_PLANNING_OPERATOR_HOLD_POINT_PACKET.md",
        "tests/test_phase28_step28_implementation_sandbox_pilot_preflight_planning_operator_hold_point_packet.py",
    ]:
        assert rel in script

