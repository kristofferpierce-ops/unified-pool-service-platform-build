from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts/phase32_step10_production_like_rollout_readiness_final_boundary_confirmation_packet.ps1"
UI_PAGE = REPO / "ui/pages/1226_Phase32_Step10_Implementation_Production_Like_Rollout_Readiness_Final_Boundary_Confirmation_Packet.py"
DOC = REPO / "docs/PHASE32_STEP10_PRODUCTION_LIKE_ROLLOUT_READINESS_FINAL_BOUNDARY_CONFIRMATION_PACKET.md"
TEST = REPO / "tests/test_phase32_step10_production_like_rollout_readiness_final_boundary_confirmation_packet.py"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


def test_phase32_step10_files_exist():
    assert SCRIPT.exists()
    assert UI_PAGE.exists()
    assert DOC.exists()
    assert TEST.exists()


def test_phase32_step10_launcher_supports_optimized_actions():
    script = read(SCRIPT)
    assert 'ValidateSet("status", "apply", "smoke", "packet", "all")' in script
    assert "APPLY PASS: Phase 32 Step 10" in script
    assert "SMOKE TEST PASS: Phase 32 Step 10" in script


def test_phase32_step10_safety_markers_present():
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


def test_phase32_step10_does_not_enable_runtime_or_phase33():
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


def test_phase32_step10_doc_declares_no_phase33_boundary():
    doc = read(DOC).lower()
    assert "phase33_start=false" in doc
    assert "phase33_boundary_creation=false" in doc
    assert "no_live_user_access=true" in doc
    assert "no_bridge_post=true" in doc or "no bridge post" in doc
    assert "no_network_sockets=true" in doc or "no network sockets" in doc


def test_phase32_step10_ui_is_reference_only():
    ui = read(UI_PAGE)
    assert "reference-only" in ui
    assert "Phase 32" in ui or "phase32" in ui
    assert "live LACRM writes" in ui


def test_phase32_step10_prior_step_is_recorded():
    combined = read(SCRIPT) + read(DOC) + read(UI_PAGE)
    assert "Phase 32 Step 9 - Phase 20 Network Transport Implementation Production-Like Rollout Readiness Closeout Index Packet" in combined


def test_phase32_step10_uses_exact_four_step_files():
    script = read(SCRIPT)
    for rel in [
        "scripts/phase32_step10_production_like_rollout_readiness_final_boundary_confirmation_packet.ps1",
        "ui/pages/1226_Phase32_Step10_Implementation_Production_Like_Rollout_Readiness_Final_Boundary_Confirmation_Packet.py",
        "docs/PHASE32_STEP10_PRODUCTION_LIKE_ROLLOUT_READINESS_FINAL_BOUNDARY_CONFIRMATION_PACKET.md",
        "tests/test_phase32_step10_production_like_rollout_readiness_final_boundary_confirmation_packet.py",
    ]:
        assert rel in script


