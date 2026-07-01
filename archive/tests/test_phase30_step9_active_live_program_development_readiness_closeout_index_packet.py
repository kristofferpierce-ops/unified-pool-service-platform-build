from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts/phase30_step9_active_live_program_development_readiness_closeout_index_packet.ps1"
UI_PAGE = REPO / "ui/pages/985_Phase30_Step9_Implementation_Active_Live_Program_Development_Readiness_Closeout_Index_Packet.py"
DOC = REPO / "docs/PHASE30_STEP9_ACTIVE_LIVE_PROGRAM_DEVELOPMENT_READINESS_CLOSEOUT_INDEX_PACKET.md"
TEST = REPO / "tests/test_phase30_step9_active_live_program_development_readiness_closeout_index_packet.py"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


def test_phase30_step9_files_exist():
    assert SCRIPT.exists()
    assert UI_PAGE.exists()
    assert DOC.exists()
    assert TEST.exists()


def test_phase30_step9_launcher_supports_optimized_actions():
    script = read(SCRIPT)
    assert 'ValidateSet("status", "apply", "smoke", "packet", "all")' in script
    assert "APPLY PASS: Phase 30 Step 9" in script
    assert "SMOKE TEST PASS: Phase 30 Step 9" in script


def test_phase30_step9_safety_markers_present():
    combined = read(SCRIPT) + read(DOC) + read(UI_PAGE)
    for marker in [
        "planning_only",
        "no_real_bridge_http_client",
        "no_network_transport_implementation",
        "no_bridge_post",
        "no_network_sockets",
        "phase30_execution_start",
        "phase30_implementation_start",
        "implementation_phase_start",
        "active_live_program_start",
        "active_live_program_execution_start",
        "live_user_access_start",
        "phase31_start",
        "phase31_boundary_creation",
        "no_live_user_access",
        "lacrm_default_mode",
        "live_write_disabled",
        "live_write_unarmed",
    ]:
        assert marker in combined


def test_phase30_step9_does_not_enable_runtime_or_phase31():
    operational_text = read(SCRIPT) + read(DOC) + read(UI_PAGE)
    forbidden_enabled = [
        ("phase31_start", "true"),
        ("phase31_boundary_creation", "true"),
        ("phase30_execution_start", "true"),
        ("phase30_implementation_start", "true"),
        ("implementation_phase_start", "true"),
        ("active_live_program_start", "true"),
        ("active_live_program_execution_start", "true"),
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


def test_phase30_step9_doc_declares_no_phase31_boundary():
    doc = read(DOC).lower()
    assert "phase31_start=false" in doc
    assert "phase31_boundary_creation=false" in doc
    assert "no_live_user_access=true" in doc
    assert "no_bridge_post=true" in doc or "no bridge post" in doc
    assert "no_network_sockets=true" in doc or "no network sockets" in doc


def test_phase30_step9_ui_is_reference_only():
    ui = read(UI_PAGE)
    assert "reference-only" in ui
    assert "Phase 30" in ui or "phase30" in ui
    assert "live LACRM writes" in ui


def test_phase30_step9_prior_step_is_recorded():
    combined = read(SCRIPT) + read(DOC) + read(UI_PAGE)
    assert "Phase 30 Step 8 - Phase 20 Network Transport Implementation Active Live Program Development Readiness Operator Hold Point Packet" in combined


def test_phase30_step9_uses_exact_four_step_files():
    script = read(SCRIPT)
    for rel in [
        "scripts/phase30_step9_active_live_program_development_readiness_closeout_index_packet.ps1",
        "ui/pages/985_Phase30_Step9_Implementation_Active_Live_Program_Development_Readiness_Closeout_Index_Packet.py",
        "docs/PHASE30_STEP9_ACTIVE_LIVE_PROGRAM_DEVELOPMENT_READINESS_CLOSEOUT_INDEX_PACKET.md",
        "tests/test_phase30_step9_active_live_program_development_readiness_closeout_index_packet.py",
    ]:
        assert rel in script

