from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts/phase32_step44_production_like_rollout_no_write_dry_run_verification_planning_safety_disposition_planning_packet.ps1"
UI_PAGE = REPO / "ui/pages/1260_Phase32_Step44_Implementation_Production_Like_Rollout_No_Write_Dry_Run_Verification_Planning_Safety_Disposition_Planning_Packet.py"
DOC = REPO / "docs/PHASE32_STEP44_PRODUCTION_LIKE_ROLLOUT_NO_WRITE_DRY_RUN_VERIFICATION_PLANNING_SAFETY_DISPOSITION_PLANNING_PACKET.md"
TEST = REPO / "tests/test_phase32_step44_production_like_rollout_no_write_dry_run_verification_planning_safety_disposition_planning_packet.py"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


def test_phase32_step44_files_exist():
    assert SCRIPT.exists()
    assert UI_PAGE.exists()
    assert DOC.exists()
    assert TEST.exists()


def test_phase32_step44_launcher_supports_optimized_actions():
    script = read(SCRIPT)
    assert 'ValidateSet("status", "apply", "smoke", "packet", "all")' in script
    assert "APPLY PASS: Phase 32 Step 44" in script
    assert "SMOKE TEST PASS: Phase 32 Step 44" in script


def test_phase32_step44_safety_markers_present():
    combined = read(SCRIPT) + read(DOC) + read(UI_PAGE)
    for marker in [
        "planning_only",
        "no_real_bridge_http_client",
        "no_network_transport_implementation",
        "no_bridge_post",
        "no_network_sockets",
        "phase32_execution_start",
        "phase32_implementation_start",
        "implementation_phase_start",
        "controlled_active_program_start",
        "controlled_active_program_execution_start",
        "production_like_rollout_start",
        "production_like_rollout_execution_start",
        "live_user_access_start",
        "phase33_start",
        "phase33_boundary_creation",
        "no_live_user_access",
        "lacrm_default_mode",
        "live_write_disabled",
        "live_write_unarmed",
    ]:
        assert marker in combined


def test_phase32_step44_does_not_enable_runtime_or_phase33():
    operational_text = read(SCRIPT) + read(DOC) + read(UI_PAGE)
    forbidden_enabled = [
        ("phase33_start", "true"),
        ("phase33_boundary_creation", "true"),
        ("phase32_execution_start", "true"),
        ("phase32_implementation_start", "true"),
        ("implementation_phase_start", "true"),
        ("controlled_active_program_start", "true"),
        ("controlled_active_program_execution_start", "true"),
        ("production_like_rollout_start", "true"),
        ("production_like_rollout_execution_start", "true"),
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


def test_phase32_step44_doc_declares_no_phase33_boundary():
    doc = read(DOC).lower()
    assert "phase33_start=false" in doc
    assert "phase33_boundary_creation=false" in doc
    assert "no_live_user_access=true" in doc
    assert "no_bridge_post=true" in doc or "no bridge post" in doc
    assert "no_network_sockets=true" in doc or "no network sockets" in doc


def test_phase32_step44_ui_is_reference_only():
    ui = read(UI_PAGE)
    assert "reference-only" in ui
    assert "Phase 32" in ui or "phase32" in ui
    assert "live LACRM writes" in ui


def test_phase32_step44_prior_step_is_recorded():
    combined = read(SCRIPT) + read(DOC) + read(UI_PAGE)
    assert "Phase 32 Step 43 - Phase 20 Network Transport Implementation Production-Like Rollout No-Write Dry Run Verification Planning Evidence Gap Review Packet" in combined


def test_phase32_step44_uses_exact_four_step_files():
    script = read(SCRIPT)
    for rel in [
        "scripts/phase32_step44_production_like_rollout_no_write_dry_run_verification_planning_safety_disposition_planning_packet.ps1",
        "ui/pages/1260_Phase32_Step44_Implementation_Production_Like_Rollout_No_Write_Dry_Run_Verification_Planning_Safety_Disposition_Planning_Packet.py",
        "docs/PHASE32_STEP44_PRODUCTION_LIKE_ROLLOUT_NO_WRITE_DRY_RUN_VERIFICATION_PLANNING_SAFETY_DISPOSITION_PLANNING_PACKET.md",
        "tests/test_phase32_step44_production_like_rollout_no_write_dry_run_verification_planning_safety_disposition_planning_packet.py",
    ]:
        assert rel in script


