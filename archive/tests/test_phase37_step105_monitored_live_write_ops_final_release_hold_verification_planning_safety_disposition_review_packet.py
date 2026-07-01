import pathlib
import subprocess
import sys

REPO = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts/phase37_step105_monitored_live_write_ops_final_release_hold_verification_planning_safety_disposition_review_packet.ps1"
UI = REPO / "ui/pages/1921_Phase37_Step105_Monitored_Live_Write_Ops_Final_Release_Hold_Verification_Safety_Review.py"
DOC = REPO / "docs/PHASE37_STEP105_MONITORED_LIVE_WRITE_OPS_FINAL_RELEASE_HOLD_VERIFICATION_PLANNING_SAFETY_DISPOSITION_REVIEW_PACKET.md"
TEST = REPO / "tests/test_phase37_step105_monitored_live_write_ops_final_release_hold_verification_planning_safety_disposition_review_packet.py"


def read(path: pathlib.Path) -> str:
    return path.read_text(encoding="utf-8")


def test_phase37_step_105_files_exist() -> None:
    for path in (SCRIPT, UI, DOC, TEST):
        assert path.exists(), f"Missing expected file: {path}"


def test_phase37_step_105_launcher_has_valid_param_block() -> None:
    text = read(SCRIPT)
    assert text.lstrip().startswith("param(")
    assert "[string]$RepoRoot" in text
    assert "[ValidateSet(" in text


def test_phase37_step_105_payloads_are_bom_free() -> None:
    for path in (SCRIPT, UI, DOC, TEST):
        assert not path.read_bytes().startswith(b"\xef\xbb\xbf"), f"BOM detected in {path}"


def test_phase37_step_105_safety_markers_present() -> None:
    text = read(SCRIPT) + "\n" + read(UI) + "\n" + read(DOC)
    required = [
        "planning_only=true",
        "no_real_bridge_http_client=true",
        "no_network_transport_implementation=true",
        "no_bridge_post=true",
        "no_network_sockets=true",
        "phase37_execution_start=false",
        "phase37_implementation_start=false",
        "implementation_phase_start=false",
        "trusted_production_monitored_live_write_operations_start=false",
        "trusted_production_monitored_live_write_operations_execution_start=false",
        "monitored_live_write_operations_start=false",
        "monitored_live_write_operations_execution_start=false",
        "live_write_activation_start=false",
        "live_write_apply_start=false",
        "live_user_access_start=false",
        "no_live_user_access=true",
        "no_live_write_activation=true",
        "no_live_write_apply=true",
        "phase38_start=false",
        "phase38_boundary_creation=false",
        "lacrm_default_mode=dry_run",
        "live_write_disabled=true",
        "live_write_unarmed=true",
    ]
    for marker in required:
        assert marker in text


def test_phase37_step_105_forbidden_runtime_markers_not_enabled() -> None:
    compact = (read(SCRIPT) + "\n" + read(UI) + "\n" + read(DOC)).replace(" ", "").lower()
    forbidden_true = [
        "phase38_start=true",
        "phase38_boundary_creation=true",
        "phase37_execution_start=true",
        "phase37_implementation_start=true",
        "trusted_production_monitored_live_write_operations_start=true",
        "trusted_production_monitored_live_write_operations_execution_start=true",
        "monitored_live_write_operations_start=true",
        "monitored_live_write_operations_execution_start=true",
        "live_write_activation_start=true",
        "live_write_apply_start=true",
        "live_user_access_start=true",
        "no_live_user_access=false",
        "no_live_write_activation=false",
        "no_live_write_apply=false",
    ]
    for marker in forbidden_true:
        assert marker not in compact


def test_phase37_step_105_launcher_smoke_passes() -> None:
    result = subprocess.run(
        ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(SCRIPT), "-RepoRoot", str(REPO), "-Action", "smoke"],
        check=False,
        text=True,
        capture_output=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "SMOKE TEST PASS" in result.stdout


def test_phase37_step_105_ui_compiles() -> None:
    result = subprocess.run([sys.executable, "-m", "py_compile", str(UI)], check=False, text=True, capture_output=True)
    assert result.returncode == 0, result.stdout + result.stderr


def test_phase37_step_105_literal_pass_markers_present() -> None:
    text = read(SCRIPT)
    assert "APPLY PASS" in text
    assert "SMOKE TEST PASS" in text


def test_phase37_step_105_stays_inside_phase37() -> None:
    text = read(SCRIPT) + "\n" + read(UI) + "\n" + read(DOC)
    assert "Phase 37" in text
    assert "phase38_boundary_creation=false" in text or "phase38_boundary_creation = $false" in text