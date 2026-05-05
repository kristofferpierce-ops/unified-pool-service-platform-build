from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts/phase33_step8_trusted_production_rollout_readiness_operator_hold_point_packet.ps1"
UI_PAGE = REPO / "ui/pages/1344_Phase33_Step8_Implementation_Trusted_Production_Rollout_Readiness_Operator_Hold_Point_Packet.py"
DOC = REPO / "docs/PHASE33_STEP8_TRUSTED_PRODUCTION_ROLLOUT_READINESS_OPERATOR_HOLD_POINT_PACKET.md"
TEST = REPO / "tests/test_phase33_step8_trusted_production_rollout_readiness_operator_hold_point_packet.py"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


def test_phase33_step8_files_exist():
    assert SCRIPT.exists()
    assert UI_PAGE.exists()
    assert DOC.exists()
    assert TEST.exists()


def test_phase33_step8_launcher_supports_optimized_actions():
    script = read(SCRIPT)
    assert 'ValidateSet("status", "apply", "smoke", "packet", "all")' in script
    assert "APPLY PASS: Phase 33 Step 8" in script
    assert "SMOKE TEST PASS: Phase 33 Step 8" in script


def test_phase33_step8_safety_markers_present():
    combined = read(SCRIPT) + read(DOC) + read(UI_PAGE)
    for marker in [
        "planning_only",
        "no_real_bridge_http_client",
        "no_network_transport_implementation",
        "no_bridge_post",
        "no_network_sockets",
        "phase33_execution_start",
        "phase33_implementation_start",
        "implementation_phase_start",
        "controlled_active_program_start",
        "controlled_active_program_execution_start",
        "trusted_production_rollout_start",
        "trusted_production_rollout_execution_start",
        "live_user_access_start",
        "phase34_start",
        "phase34_boundary_creation",
        "no_live_user_access",
        "lacrm_default_mode",
        "live_write_disabled",
        "live_write_unarmed",
    ]:
        assert marker in combined


def test_phase33_step8_does_not_enable_runtime_or_phase34():
    operational_text = read(SCRIPT) + read(DOC) + read(UI_PAGE)
    forbidden_enabled = [
        ("phase34_start", "true"),
        ("phase34_boundary_creation", "true"),
        ("phase33_execution_start", "true"),
        ("phase33_implementation_start", "true"),
        ("implementation_phase_start", "true"),
        ("controlled_active_program_start", "true"),
        ("controlled_active_program_execution_start", "true"),
        ("trusted_production_rollout_start", "true"),
        ("trusted_production_rollout_execution_start", "true"),
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


def test_phase33_step8_doc_declares_no_phase34_boundary():
    doc = read(DOC).lower()
    assert "phase34_start=false" in doc
    assert "phase34_boundary_creation=false" in doc
    assert "no_live_user_access=true" in doc
    assert "no_bridge_post=true" in doc or "no bridge post" in doc
    assert "no_network_sockets=true" in doc or "no network sockets" in doc


def test_phase33_step8_ui_is_reference_only():
    ui = read(UI_PAGE)
    assert "reference-only" in ui
    assert "Phase 33" in ui or "phase33" in ui
    assert "live LACRM writes" in ui


def test_phase33_step8_prior_step_is_recorded():
    combined = read(SCRIPT) + read(DOC) + read(UI_PAGE)
    assert "Phase 33 Step 7 - Phase 20 Network Transport Implementation Trusted Production Rollout Readiness Approval Readiness Packet" in combined


def test_phase33_step8_uses_exact_four_step_files():
    script = read(SCRIPT)
    for rel in [
        "scripts/phase33_step8_trusted_production_rollout_readiness_operator_hold_point_packet.ps1",
        "ui/pages/1344_Phase33_Step8_Implementation_Trusted_Production_Rollout_Readiness_Operator_Hold_Point_Packet.py",
        "docs/PHASE33_STEP8_TRUSTED_PRODUCTION_ROLLOUT_READINESS_OPERATOR_HOLD_POINT_PACKET.md",
        "tests/test_phase33_step8_trusted_production_rollout_readiness_operator_hold_point_packet.py",
    ]:
        assert rel in script


