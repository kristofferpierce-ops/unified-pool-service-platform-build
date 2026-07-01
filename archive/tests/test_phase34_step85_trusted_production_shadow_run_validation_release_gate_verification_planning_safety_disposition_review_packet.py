from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts/phase34_step85_trusted_production_shadow_run_validation_release_gate_verification_planning_safety_disposition_review_packet.ps1"
UI_PAGE = REPO / "ui/pages/1541_Phase34_Step85_Shadow_Run_Release_Gate_Verification_Safety_Review.py"
DOC = REPO / "docs/PHASE34_STEP85_TRUSTED_PRODUCTION_SHADOW_RUN_VALIDATION_RELEASE_GATE_VERIFICATION_PLANNING_SAFETY_DISPOSITION_REVIEW_PACKET.md"
TEST = REPO / "tests/test_phase34_step85_trusted_production_shadow_run_validation_release_gate_verification_planning_safety_disposition_review_packet.py"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


def test_phase34_step85_files_exist():
    assert SCRIPT.exists()
    assert UI_PAGE.exists()
    assert DOC.exists()
    assert TEST.exists()


def test_phase34_step85_launcher_supports_optimized_actions():
    script = read(SCRIPT)
    assert 'ValidateSet("status", "apply", "smoke", "packet", "all")' in script
    assert "APPLY PASS: Phase 34 Step 85" in script
    assert "SMOKE TEST PASS: Phase 34 Step 85" in script


def test_phase34_step85_safety_markers_present():
    combined = read(SCRIPT) + read(DOC) + read(UI_PAGE)
    for marker in [
        "planning_only",
        "no_real_bridge_http_client",
        "no_network_transport_implementation",
        "no_bridge_post",
        "no_network_sockets",
        "phase34_execution_start",
        "phase34_implementation_start",
        "implementation_phase_start",
        "controlled_active_program_start",
        "controlled_active_program_execution_start",
        "trusted_production_shadow_run_validation_start",
        "trusted_production_shadow_run_validation_execution_start",
        "live_user_access_start",
        "phase35_start",
        "phase35_boundary_creation",
        "no_live_user_access",
        "lacrm_default_mode",
        "live_write_disabled",
        "live_write_unarmed",
    ]:
        assert marker in combined


def test_phase34_step85_does_not_enable_runtime_or_phase35():
    operational_text = read(SCRIPT) + read(DOC) + read(UI_PAGE)
    forbidden_enabled = [
        ("phase35_start", "true"),
        ("phase35_boundary_creation", "true"),
        ("phase34_execution_start", "true"),
        ("phase34_implementation_start", "true"),
        ("implementation_phase_start", "true"),
        ("controlled_active_program_start", "true"),
        ("controlled_active_program_execution_start", "true"),
        ("trusted_production_shadow_run_validation_start", "true"),
        ("trusted_production_shadow_run_validation_execution_start", "true"),
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


def test_phase34_step85_doc_declares_no_phase35_boundary():
    doc = read(DOC).lower()
    assert "phase35_start=false" in doc
    assert "phase35_boundary_creation=false" in doc
    assert "no_live_user_access=true" in doc
    assert "no_bridge_post=true" in doc or "no bridge post" in doc
    assert "no_network_sockets=true" in doc or "no network sockets" in doc


def test_phase34_step85_ui_is_reference_only():
    ui = read(UI_PAGE)
    assert "reference-only" in ui
    assert "Phase 34" in ui or "phase34" in ui
    assert "live LACRM writes" in ui


def test_phase34_step85_prior_step_is_recorded():
    combined = read(SCRIPT) + read(DOC) + read(UI_PAGE)
    assert "Phase 34 Step 84 - Phase 20 Network Transport Implementation Trusted Production Shadow Run Validation Release Gate Verification Planning Safety Disposition Planning Packet" in combined


def test_phase34_step85_uses_exact_four_step_files():
    script = read(SCRIPT)
    for rel in [
        "scripts/phase34_step85_trusted_production_shadow_run_validation_release_gate_verification_planning_safety_disposition_review_packet.ps1",
        "ui/pages/1541_Phase34_Step85_Shadow_Run_Release_Gate_Verification_Safety_Review.py",
        "docs/PHASE34_STEP85_TRUSTED_PRODUCTION_SHADOW_RUN_VALIDATION_RELEASE_GATE_VERIFICATION_PLANNING_SAFETY_DISPOSITION_REVIEW_PACKET.md",
        "tests/test_phase34_step85_trusted_production_shadow_run_validation_release_gate_verification_planning_safety_disposition_review_packet.py",
    ]:
        assert rel in script


