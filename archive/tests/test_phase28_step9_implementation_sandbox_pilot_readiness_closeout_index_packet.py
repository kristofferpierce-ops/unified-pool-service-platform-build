from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/phase28_step9_implementation_sandbox_pilot_readiness_closeout_index_packet.ps1"
UI_PAGE = ROOT / "ui/pages/745_Phase28_Step9_Implementation_Sandbox_Pilot_Readiness_Closeout_Index_Packet.py"
DOC = ROOT / "docs/PHASE28_STEP9_IMPLEMENTATION_SANDBOX_PILOT_READINESS_CLOSEOUT_INDEX_PACKET.md"
TEST_FILE = ROOT / "tests/test_phase28_step9_implementation_sandbox_pilot_readiness_closeout_index_packet.py"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


def test_phase28_step9_files_exist():
    assert SCRIPT.exists()
    assert UI_PAGE.exists()
    assert DOC.exists()
    assert TEST_FILE.exists()


def test_phase28_step9_launcher_supports_optimized_actions():
    script = read(SCRIPT)
    assert 'ValidateSet("status", "apply", "smoke", "packet", "all")' in script
    assert "APPLY PASS: Phase 28 Step 9" in script
    assert "SMOKE TEST PASS: Phase 28 Step 9" in script
    assert "implementation_sandbox_pilot_readiness_closeout_index_opened_by_packet" in script


def test_phase28_step9_planning_only_markers_present():
    combined = "\n".join(read(path) for path in (SCRIPT, UI_PAGE, DOC))
    required = [
        "planning_only", "no_real_bridge_http_client", "no_network_transport_implementation",
        "no_bridge_post", "no_network_sockets", "phase28_execution_start",
        "phase28_implementation_start", "implementation_phase_start", "sandbox_pilot_start",
        "sandbox_pilot_execution_start", "phase29_start", "phase29_boundary_creation",
        "lacrm_default_mode", "dry_run", "live_write_disabled", "live_write_unarmed",
        "implementation_sandbox_pilot_readiness_closeout_index_mode", "implementation_sandbox_pilot_readiness_closeout_index_write", "implementation_sandbox_pilot_readiness_closeout_index_record_creation",
    ]
    for marker in required:
        assert marker in combined


def test_phase28_step9_forbidden_runtime_markers_not_enabled():
    operational_text = "\n".join(read(path).lower() for path in (SCRIPT, UI_PAGE, DOC))
    forbidden_enabled = [
        "phase29_start=true", "phase29_boundary_creation=true", "phase28_execution_start=true",
        "phase28_implementation_start=true", "implementation_phase_start=true",
        "sandbox_pilot_start=true", "sandbox_pilot_execution_start=true",
        "network_transport_runtime_start=true", "bridge_transport_runtime_start=true",
        "no_network_transport_implementation=false", "no_bridge_post=false",
        "no_network_sockets=false", "live_write_disabled=false", "live_write_unarmed=false",
    ]
    for marker in forbidden_enabled:
        assert marker not in operational_text


def test_phase28_step9_doc_declares_no_phase28_boundary():
    doc = read(DOC).lower()
    assert "phase29_start=false" in doc
    assert "phase29_boundary_creation=false" in doc
    assert "no bridge post" in doc or "no_bridge_post=true" in doc
    assert "no network sockets" in doc or "no_network_sockets=true" in doc


def test_phase28_step9_ui_is_reference_only():
    ui = read(UI_PAGE)
    assert "reference-only" in ui
    assert "Phase 29" in ui or "phase29" in ui
    assert "live LACRM writes" in ui


def test_phase28_step9_prior_step_is_recorded():
    combined = read(SCRIPT) + read(DOC) + read(UI_PAGE)
    assert "Phase 28 Step 8 - Phase 20 Network Transport Implementation Sandbox Pilot Readiness Operator Hold Point Packet" in combined


def test_phase28_step9_uses_exact_four_step_files():
    script = read(SCRIPT)
    for rel in ["scripts/phase28_step9_implementation_sandbox_pilot_readiness_closeout_index_packet.ps1", "ui/pages/745_Phase28_Step9_Implementation_Sandbox_Pilot_Readiness_Closeout_Index_Packet.py", "docs/PHASE28_STEP9_IMPLEMENTATION_SANDBOX_PILOT_READINESS_CLOSEOUT_INDEX_PACKET.md", "tests/test_phase28_step9_implementation_sandbox_pilot_readiness_closeout_index_packet.py"]:
        assert rel in script
