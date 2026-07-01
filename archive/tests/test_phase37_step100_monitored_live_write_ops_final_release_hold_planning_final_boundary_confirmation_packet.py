from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'scripts/phase37_step100_monitored_live_write_ops_final_release_hold_planning_final_boundary_confirmation_packet.ps1'
UI = ROOT / 'ui/pages/1916_Phase37_Step100_Monitored_Live_Write_Ops_Final_Release_Hold_Final_Boundary.py'
DOC = ROOT / 'docs/PHASE37_STEP100_MONITORED_LIVE_WRITE_OPS_FINAL_RELEASE_HOLD_PLANNING_FINAL_BOUNDARY_CONFIRMATION_PACKET.md'


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_phase37_step_100_files_exist() -> None:
    assert SCRIPT.exists()
    assert UI.exists()
    assert DOC.exists()


def test_phase37_step_100_launcher_has_valid_param_block() -> None:
    text = read(SCRIPT)
    assert text.startswith("param(")
    assert not text.startswith("\ufeff")


def test_phase37_step_100_launcher_markers() -> None:
    text = read(SCRIPT)
    assert "APPLY PASS" in text
    assert "SMOKE TEST PASS" in text
    assert "Set-StrictMode" in text


def test_phase37_step_100_ui_page_smoke_markers() -> None:
    text = read(UI)
    assert "streamlit" in text
    assert "SMOKE TEST PASS" in text
    assert "APPLY PASS" in text


def test_phase37_step_100_doc_mentions_planning_only() -> None:
    text = read(DOC).lower()
    assert "planning-only" in text
    assert "does not activate live writes" in text


def test_phase37_step_100_required_safe_markers_present() -> None:
    compact = (read(SCRIPT) + "\n" + read(UI) + "\n" + read(DOC)).replace(" ", "").lower()
    required = ['planning_only=true', 'no_real_bridge_http_client=true', 'no_network_transport_implementation=true', 'no_bridge_post=true', 'no_network_sockets=true', 'phase37_execution_start=false', 'phase37_implementation_start=false', 'implementation_phase_start=false', 'trusted_production_monitored_live_write_operations_start=false', 'trusted_production_monitored_live_write_operations_execution_start=false', 'monitored_live_write_operations_start=false', 'monitored_live_write_operations_execution_start=false', 'live_write_activation_start=false', 'live_write_apply_start=false', 'live_user_access_start=false', 'no_live_user_access=true', 'no_live_write_activation=true', 'no_live_write_apply=true', 'phase38_start=false', 'phase38_boundary_creation=false', 'lacrm_default_mode=dry_run', 'live_write_disabled=true', 'live_write_unarmed=true']
    for marker in required:
        assert marker in compact


def test_phase37_step_100_forbidden_runtime_markers_not_enabled() -> None:
    compact = (read(SCRIPT) + "\n" + read(UI) + "\n" + read(DOC)).replace(" ", "").lower()
    forbidden_true = ['phase38_start=true', 'phase38_boundary_creation=true', 'phase37_execution_start=true', 'phase37_implementation_start=true', 'trusted_production_monitored_live_write_operations_start=true', 'trusted_production_monitored_live_write_operations_execution_start=true', 'monitored_live_write_operations_start=true', 'monitored_live_write_operations_execution_start=true', 'live_write_activation_start=true', 'live_write_apply_start=true', 'live_user_access_start=true', 'no_live_user_access=false', 'no_live_write_activation=false', 'no_live_write_apply=false']
    for marker in forbidden_true:
        assert marker not in compact


def test_phase37_step_100_no_phase38_files_created_by_payload() -> None:
    assert "phase38" in read(SCRIPT).lower()
    assert "phase38_start=false" in read(DOC).replace(" ", "").lower()
    assert not any(
        any((ROOT / folder).glob("*phase38*"))
        for folder in ["scripts", "docs", "tests", "ui/pages"]
    )
