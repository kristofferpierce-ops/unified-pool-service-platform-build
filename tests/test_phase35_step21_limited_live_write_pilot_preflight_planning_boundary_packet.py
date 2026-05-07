from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts/phase35_step21_limited_live_write_pilot_preflight_planning_boundary_packet.ps1"
UI_PAGE = REPO / "ui/pages/1597_Phase35_Step21_Live_Write_Pilot_Preflight_Boundary.py"
DOC = REPO / "docs/PHASE35_STEP21_LIMITED_LIVE_WRITE_PILOT_PREFLIGHT_PLANNING_BOUNDARY_PACKET.md"
TEST = REPO / "tests/test_phase35_step21_limited_live_write_pilot_preflight_planning_boundary_packet.py"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


def test_phase35_step21_files_exist():
    assert SCRIPT.exists()
    assert UI_PAGE.exists()
    assert DOC.exists()
    assert TEST.exists()


def test_phase35_step21_launcher_supports_optimized_actions():
    script = read(SCRIPT)
    assert 'ValidateSet("status", "apply", "smoke", "packet", "all")' in script
    assert "APPLY PASS: Phase 35 Step 21" in script
    assert "SMOKE TEST PASS: Phase 35 Step 21" in script


def test_phase35_step21_safety_markers_present():
    combined = read(SCRIPT) + read(DOC) + read(UI_PAGE)
    for marker in [
        "planning_only",
        "no_real_bridge_http_client",
        "no_network_transport_implementation",
        "no_bridge_post",
        "no_network_sockets",
        "phase35_execution_start",
        "phase35_implementation_start",
        "implementation_phase_start",
        "trusted_production_limited_live_write_pilot_start",
        "trusted_production_limited_live_write_pilot_execution_start",
        "limited_live_write_pilot_start",
        "limited_live_write_pilot_execution_start",
        "live_write_activation_start",
        "live_user_access_start",
        "phase36_start",
        "phase36_boundary_creation",
        "no_live_user_access",
        "no_live_write_activation",
        "lacrm_default_mode",
        "live_write_disabled",
        "live_write_unarmed",
    ]:
        assert marker in combined


def test_phase35_step21_does_not_enable_runtime_or_phase36():
    operational_text = read(SCRIPT) + read(DOC) + read(UI_PAGE)
    forbidden_enabled = [
        ("phase36_start", "true"),
        ("phase36_boundary_creation", "true"),
        ("phase35_execution_start", "true"),
        ("phase35_implementation_start", "true"),
        ("implementation_phase_start", "true"),
        ("trusted_production_limited_live_write_pilot_start", "true"),
        ("trusted_production_limited_live_write_pilot_execution_start", "true"),
        ("limited_live_write_pilot_start", "true"),
        ("limited_live_write_pilot_execution_start", "true"),
        ("live_write_activation_start", "true"),
        ("live_user_access_start", "true"),
        ("network_transport_runtime_start", "true"),
        ("bridge_transport_runtime_start", "true"),
        ("no_network_transport_implementation", "false"),
        ("no_bridge_post", "false"),
        ("no_network_sockets", "false"),
        ("no_live_user_access", "false"),
        ("no_live_write_activation", "false"),
        ("live_write_disabled", "false"),
        ("live_write_unarmed", "false"),
    ]
    for name, value in forbidden_enabled:
        marker = f"{name}={value}"
        assert marker not in operational_text


def test_phase35_step21_doc_declares_no_phase36_boundary():
    doc = read(DOC).lower()
    assert "phase36_start=false" in doc
    assert "phase36_boundary_creation=false" in doc
    assert "no_live_user_access=true" in doc
    assert "no_live_write_activation=true" in doc
    assert "no_bridge_post=true" in doc or "no bridge post" in doc
    assert "no_network_sockets=true" in doc or "no network sockets" in doc


def test_phase35_step21_ui_is_reference_only():
    ui = read(UI_PAGE)
    assert "reference-only" in ui
    assert "Phase 35" in ui or "phase35" in ui
    assert "live LACRM writes" in ui


def test_phase35_step21_prior_step_is_recorded():
    combined = read(SCRIPT) + read(DOC) + read(UI_PAGE)
    assert "Phase 35 Step 20 - Phase 20 Network Transport Implementation Trusted Production Limited Live Write Pilot Guardrail Verification Final Boundary Confirmation Packet" in combined


def test_phase35_step21_uses_exact_four_step_files():
    script = read(SCRIPT)
    for rel in [
        "scripts/phase35_step21_limited_live_write_pilot_preflight_planning_boundary_packet.ps1",
        "ui/pages/1597_Phase35_Step21_Live_Write_Pilot_Preflight_Boundary.py",
        "docs/PHASE35_STEP21_LIMITED_LIVE_WRITE_PILOT_PREFLIGHT_PLANNING_BOUNDARY_PACKET.md",
        "tests/test_phase35_step21_limited_live_write_pilot_preflight_planning_boundary_packet.py",
    ]:
        assert rel in script


