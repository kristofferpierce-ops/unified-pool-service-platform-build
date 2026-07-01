from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts/phase31_step27_controlled_active_program_operation_preflight_planning_approval_readiness_packet.ps1"
UI_PAGE = REPO / "ui/pages/1123_Phase31_Step27_Implementation_Controlled_Active_Program_Operation_Preflight_Planning_Approval_Readiness_Packet.py"
DOC = REPO / "docs/PHASE31_STEP27_CONTROLLED_ACTIVE_PROGRAM_OPERATION_PREFLIGHT_PLANNING_APPROVAL_READINESS_PACKET.md"
TEST = REPO / "tests/test_phase31_step27_controlled_active_program_operation_preflight_planning_approval_readiness_packet.py"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


def test_phase31_step27_files_exist():
    assert SCRIPT.exists()
    assert UI_PAGE.exists()
    assert DOC.exists()
    assert TEST.exists()


def test_phase31_step27_launcher_supports_optimized_actions():
    script = read(SCRIPT)
    assert 'ValidateSet("status", "apply", "smoke", "packet", "all")' in script
    assert "APPLY PASS: Phase 31 Step 27" in script
    assert "SMOKE TEST PASS: Phase 31 Step 27" in script


def test_phase31_step27_safety_markers_present():
    combined = read(SCRIPT) + read(DOC) + read(UI_PAGE)
    for marker in [
        "planning_only",
        "no_real_bridge_http_client",
        "no_network_transport_implementation",
        "no_bridge_post",
        "no_network_sockets",
        "phase31_execution_start",
        "phase31_implementation_start",
        "implementation_phase_start",
        "controlled_active_program_start",
        "controlled_active_program_execution_start",
        "production_like_rollout_start",
        "live_user_access_start",
        "phase32_start",
        "phase32_boundary_creation",
        "no_live_user_access",
        "lacrm_default_mode",
        "live_write_disabled",
        "live_write_unarmed",
    ]:
        assert marker in combined


def test_phase31_step27_does_not_enable_runtime_or_phase32():
    operational_text = read(SCRIPT) + read(DOC) + read(UI_PAGE)
    forbidden_enabled = [
        ("phase32_start", "true"),
        ("phase32_boundary_creation", "true"),
        ("phase31_execution_start", "true"),
        ("phase31_implementation_start", "true"),
        ("implementation_phase_start", "true"),
        ("controlled_active_program_start", "true"),
        ("controlled_active_program_execution_start", "true"),
        ("production_like_rollout_start", "true"),
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


def test_phase31_step27_doc_declares_no_phase32_boundary():
    doc = read(DOC).lower()
    assert "phase32_start=false" in doc
    assert "phase32_boundary_creation=false" in doc
    assert "no_live_user_access=true" in doc
    assert "no_bridge_post=true" in doc or "no bridge post" in doc
    assert "no_network_sockets=true" in doc or "no network sockets" in doc


def test_phase31_step27_ui_is_reference_only():
    ui = read(UI_PAGE)
    assert "reference-only" in ui
    assert "Phase 31" in ui or "phase31" in ui
    assert "live LACRM writes" in ui


def test_phase31_step27_prior_step_is_recorded():
    combined = read(SCRIPT) + read(DOC) + read(UI_PAGE)
    assert "Phase 31 Step 26 - Phase 20 Network Transport Implementation Controlled Active Program Operation Preflight Planning Approval Boundary Packet" in combined


def test_phase31_step27_uses_exact_four_step_files():
    script = read(SCRIPT)
    for rel in [
        "scripts/phase31_step27_controlled_active_program_operation_preflight_planning_approval_readiness_packet.ps1",
        "ui/pages/1123_Phase31_Step27_Implementation_Controlled_Active_Program_Operation_Preflight_Planning_Approval_Readiness_Packet.py",
        "docs/PHASE31_STEP27_CONTROLLED_ACTIVE_PROGRAM_OPERATION_PREFLIGHT_PLANNING_APPROVAL_READINESS_PACKET.md",
        "tests/test_phase31_step27_controlled_active_program_operation_preflight_planning_approval_readiness_packet.py",
    ]:
        assert rel in script


