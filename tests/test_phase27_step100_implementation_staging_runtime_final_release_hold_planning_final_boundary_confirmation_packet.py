from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/phase27_step100_implementation_staging_runtime_final_release_hold_planning_final_boundary_confirmation_packet.ps1"
UI_PAGE = ROOT / "ui/pages/716_Phase27_Step100_Implementation_Staging_Runtime_Final_Release_Hold_Planning_Final_Boundary_Confirmation_Packet.py"
DOC = ROOT / "docs/PHASE27_STEP100_IMPLEMENTATION_STAGING_RUNTIME_FINAL_RELEASE_HOLD_PLANNING_FINAL_BOUNDARY_CONFIRMATION_PACKET.md"
TEST_FILE = ROOT / "tests/test_phase27_step100_implementation_staging_runtime_final_release_hold_planning_final_boundary_confirmation_packet.py"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


def test_phase27_step100_files_exist():
    assert SCRIPT.exists()
    assert UI_PAGE.exists()
    assert DOC.exists()
    assert TEST_FILE.exists()


def test_phase27_step100_launcher_supports_optimized_actions():
    script = read(SCRIPT)
    assert 'ValidateSet("status", "apply", "smoke", "packet", "all")' in script
    assert "APPLY PASS: Phase 27 Step 100" in script
    assert "SMOKE TEST PASS: Phase 27 Step 100" in script
    assert "implementation_staging_runtime_final_release_hold_planning_final_boundary_confirmation_opened_by_packet" in script


def test_phase27_step100_planning_only_markers_present():
    combined = "\n".join(read(path) for path in (SCRIPT, UI_PAGE, DOC))
    required = [
        "planning_only", "no_real_bridge_http_client", "no_network_transport_implementation",
        "no_bridge_post", "no_network_sockets", "phase27_execution_start",
        "phase27_implementation_start", "implementation_phase_start", "staging_runtime_start",
        "staging_execution_start", "phase28_start", "phase28_boundary_creation",
        "lacrm_default_mode", "dry_run", "live_write_disabled", "live_write_unarmed",
        "implementation_staging_runtime_final_release_hold_planning_final_boundary_confirmation_mode", "implementation_staging_runtime_final_release_hold_planning_final_boundary_confirmation_write", "implementation_staging_runtime_final_release_hold_planning_final_boundary_confirmation_record_creation",
    ]
    for marker in required:
        assert marker in combined


def test_phase27_step100_forbidden_runtime_markers_not_enabled():
    operational_text = "\n".join(read(path).lower() for path in (SCRIPT, UI_PAGE, DOC))
    forbidden_enabled = [
        "phase28_start=true", "phase28_boundary_creation=true", "phase27_execution_start=true",
        "phase27_implementation_start=true", "implementation_phase_start=true",
        "staging_runtime_start=true", "staging_execution_start=true",
        "network_transport_runtime_start=true", "bridge_transport_runtime_start=true",
        "no_network_transport_implementation=false", "no_bridge_post=false",
        "no_network_sockets=false", "live_write_disabled=false", "live_write_unarmed=false",
    ]
    for marker in forbidden_enabled:
        assert marker not in operational_text


def test_phase27_step100_doc_declares_no_phase28_boundary():
    doc = read(DOC).lower()
    assert "phase28_start=false" in doc
    assert "phase28_boundary_creation=false" in doc
    assert "no bridge post" in doc or "no_bridge_post=true" in doc
    assert "no network sockets" in doc or "no_network_sockets=true" in doc


def test_phase27_step100_ui_is_reference_only():
    ui = read(UI_PAGE)
    assert "reference-only" in ui
    assert "Phase 28" in ui or "phase28" in ui
    assert "live LACRM writes" in ui


def test_phase27_step100_prior_step_is_recorded():
    combined = read(SCRIPT) + read(DOC) + read(UI_PAGE)
    assert "Phase 27 Step 99 - Phase 20 Network Transport Implementation Staging Runtime Final Release Hold Planning Closeout Index Packet" in combined


def test_phase27_step100_uses_exact_four_step_files():
    script = read(SCRIPT)
    for rel in ["scripts/phase27_step100_implementation_staging_runtime_final_release_hold_planning_final_boundary_confirmation_packet.ps1", "ui/pages/716_Phase27_Step100_Implementation_Staging_Runtime_Final_Release_Hold_Planning_Final_Boundary_Confirmation_Packet.py", "docs/PHASE27_STEP100_IMPLEMENTATION_STAGING_RUNTIME_FINAL_RELEASE_HOLD_PLANNING_FINAL_BOUNDARY_CONFIRMATION_PACKET.md", "tests/test_phase27_step100_implementation_staging_runtime_final_release_hold_planning_final_boundary_confirmation_packet.py"]:
        assert rel in script
