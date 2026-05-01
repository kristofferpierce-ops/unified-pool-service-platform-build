from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/phase27_step120_phase27_final_no_write_closeout_hold_packet.ps1"
UI_PAGE = ROOT / "ui/pages/736_Phase27_Step120_Phase27_Final_No_Write_Closeout_Hold_Packet.py"
DOC = ROOT / "docs/PHASE27_STEP120_PHASE27_FINAL_NO_WRITE_CLOSEOUT_HOLD_PACKET.md"
TEST_FILE = ROOT / "tests/test_phase27_step120_phase27_final_no_write_closeout_hold_packet.py"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


def test_phase27_step120_files_exist():
    assert SCRIPT.exists()
    assert UI_PAGE.exists()
    assert DOC.exists()
    assert TEST_FILE.exists()


def test_phase27_step120_launcher_supports_optimized_actions():
    script = read(SCRIPT)
    assert 'ValidateSet("status", "apply", "smoke", "packet", "all")' in script
    assert "APPLY PASS: Phase 27 Step 120" in script
    assert "SMOKE TEST PASS: Phase 27 Step 120" in script
    assert "phase27_final_no_write_closeout_hold_packet_only" in script


def test_phase27_step120_planning_only_markers_present():
    combined = "\n".join(read(path) for path in (SCRIPT, UI_PAGE, DOC))
    required = [
        "planning_only", "no_real_bridge_http_client", "no_network_transport_implementation",
        "no_bridge_post", "no_network_sockets", "phase27_execution_start",
        "phase27_implementation_start", "implementation_phase_start", "staging_runtime_start",
        "staging_execution_start", "phase28_start", "phase28_boundary_creation",
        "lacrm_default_mode", "dry_run", "live_write_disabled", "live_write_unarmed",
        "phase27_final_no_write_closeout_hold_mode", "phase27_final_no_write_closeout_hold_write", "phase27_final_no_write_closeout_hold_record_creation",
    ]
    for marker in required:
        assert marker in combined


def test_phase27_step120_forbidden_runtime_markers_not_enabled():
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


def test_phase27_step120_doc_declares_no_phase28_boundary():
    doc = read(DOC).lower()
    assert "phase28_start=false" in doc
    assert "phase28_boundary_creation=false" in doc
    assert "no bridge post" in doc or "no_bridge_post=true" in doc
    assert "no network sockets" in doc or "no_network_sockets=true" in doc


def test_phase27_step120_ui_is_reference_only():
    ui = read(UI_PAGE)
    assert "reference-only" in ui
    assert "Phase 28" in ui or "phase28" in ui
    assert "live LACRM writes" in ui


def test_phase27_step120_prior_step_is_recorded():
    combined = read(SCRIPT) + read(DOC) + read(UI_PAGE)
    assert "Phase 27 Step 119 - Phase 20 Network Transport Implementation Staging Runtime Final Release Result Review Planning Closeout Index Packet" in combined


def test_phase27_step120_uses_exact_four_step_files():
    script = read(SCRIPT)
    for rel in ["scripts/phase27_step120_phase27_final_no_write_closeout_hold_packet.ps1", "ui/pages/736_Phase27_Step120_Phase27_Final_No_Write_Closeout_Hold_Packet.py", "docs/PHASE27_STEP120_PHASE27_FINAL_NO_WRITE_CLOSEOUT_HOLD_PACKET.md", "tests/test_phase27_step120_phase27_final_no_write_closeout_hold_packet.py"]:
        assert rel in script
