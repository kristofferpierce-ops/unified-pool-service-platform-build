from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts/phase37_step8_monitored_live_write_ops_readiness_readiness_operator_hold_packet.ps1"
UI = REPO / "ui/pages/1824_Phase37_Step8_Monitored_Live_Write_Ops_Readiness_Operator_Hold.py"
DOC = REPO / "docs/PHASE37_STEP8_MONITORED_LIVE_WRITE_OPS_READINESS_READINESS_OPERATOR_HOLD_PACKET.md"
TEST = REPO / "tests/test_phase37_step8_monitored_live_write_ops_readiness_readiness_operator_hold_packet.py"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_phase37_step8_files_exist():
    assert SCRIPT.exists()
    assert UI.exists()
    assert DOC.exists()
    assert TEST.exists()


def test_phase37_step8_launcher_has_valid_param_block():
    text = _read(SCRIPT)
    assert text.lstrip().startswith("param(")
    assert '[string]$RepoRoot = ""' in text
    assert '[ValidateSet("status", "apply", "smoke", "packet", "all")]' in text


def test_phase37_step8_required_safety_markers_present():
    combined = "\n".join(_read(path) for path in (SCRIPT, UI, DOC))
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


def test_phase37_step8_next_phase_guards_present():
    combined = "\n".join(_read(path) for path in (SCRIPT, UI, DOC))
    assert "phase38_start" in combined
    assert "phase38_boundary_creation" in combined


def test_phase37_step8_forbidden_true_markers_absent():
    combined = "\n".join(_read(path) for path in (SCRIPT, UI, DOC)).lower().replace(" ", "")
    forbidden = [
        "phase38_start=true",
        "phase38_boundary_creation=true",
        "phase37_execution_start=true",
        "phase37_implementation_start=true",
        "live_write_activation_start=true",
        "live_write_apply_start=true",
        "live_user_access_start=true",
        "trusted_production_monitored_live_write_operations_start=true",
        "trusted_production_monitored_live_write_operations_execution_start=true",
    ]
    for marker in forbidden:
        assert marker not in combined


def test_phase37_step8_literal_pass_markers_present():
    text = _read(SCRIPT)
    assert "APPLY PASS" in text
    assert "SMOKE TEST PASS" in text


def test_phase37_step8_ui_is_planning_only_page():
    text = _read(UI)
    assert "Planning-only packet page" in text
    assert "st.set_page_config" in text
    assert "phase38_start=false" in text


def test_phase37_step8_doc_records_no_runtime_boundary():
    text = _read(DOC)
    assert "does not launch a server" in text
    assert "does not" in text
    assert "phase38_boundary_creation=false" in text
