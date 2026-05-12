from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/phase38_step9_sustained_live_write_ops_readiness_closeout_index_packet.ps1"
UI = ROOT / "ui/pages/1945_Phase38_Step9_Sustained_Live_Write_Ops_Readiness_Closeout_Index.py"
DOC = ROOT / "docs/PHASE38_STEP9_SUSTAINED_LIVE_WRITE_OPS_READINESS_CLOSEOUT_INDEX_PACKET.md"
TEST = ROOT / "tests/test_phase38_step9_sustained_live_write_ops_readiness_closeout_index_packet.py"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_phase38_step9_files_exist() -> None:
    assert SCRIPT.exists()
    assert UI.exists()
    assert DOC.exists()
    assert TEST.exists()


def test_phase38_step9_launcher_has_valid_param_block() -> None:
    text = read(SCRIPT)
    assert text.lstrip().startswith("param(")
    assert '[string]$RepoRoot = ""' in text
    assert '[ValidateSet("status", "apply", "smoke", "packet", "all")]' in text


def test_phase38_step9_required_safety_markers_present() -> None:
    combined = "\n".join(read(path) for path in (SCRIPT, UI, DOC))
    for marker in [
        "planning_only",
        "no_real_bridge_http_client",
        "no_network_transport_implementation",
        "no_bridge_post",
        "no_network_sockets",
        "no_live_user_access",
        "no_live_write_activation",
        "no_live_write_apply",
        "lacrm_default_mode",
        "live_write_disabled",
        "live_write_unarmed",
    ]:
        assert marker in combined


def test_phase38_step9_next_phase_guards_present() -> None:
    combined = "\n".join(read(path) for path in (SCRIPT, UI, DOC))
    assert "phase39_start" in combined
    assert "phase39_boundary_creation" in combined


def test_phase38_step9_forbidden_runtime_markers_not_enabled() -> None:
    compact = (read(SCRIPT) + "\n" + read(UI) + "\n" + read(DOC)).replace(" ", "").lower()
    forbidden_true = [
        "phase39_start=true",
        "phase39_boundary_creation=true",
        "phase38_execution_start=true",
        "phase38_implementation_start=true",
        "implementation_phase_start=true",
        "trusted_production_sustained_live_write_operations_start=true",
        "trusted_production_sustained_live_write_operations_execution_start=true",
        "sustained_live_write_operations_start=true",
        "sustained_live_write_operations_execution_start=true",
        "live_write_activation_start=true",
        "live_write_apply_start=true",
        "live_user_access_start=true",
        "no_live_user_access=false",
        "no_live_write_activation=false",
        "no_live_write_apply=false",
    ]
    for marker in forbidden_true:
        assert marker not in compact


def test_phase38_step9_literal_pass_markers_present() -> None:
    text = read(SCRIPT)
    assert "APPLY PASS" in text
    assert "SMOKE TEST PASS" in text


def test_phase38_step9_ui_is_planning_only_page() -> None:
    text = read(UI)
    assert "Planning-only packet page" in text
    assert "st.set_page_config" in text
    assert "phase39_start=false" in text


def test_phase38_step9_no_phase39_files_created_by_payload() -> None:
    assert "phase39" in read(SCRIPT).lower()
    assert "phase39_start=false" in read(DOC).replace(" ", "").lower()
    phase39_files = [
        path
        for folder in ["scripts", "docs", "tests", "ui/pages"]
        for path in (ROOT / folder).glob("*phase39*")
    ]
    assert not phase39_files
