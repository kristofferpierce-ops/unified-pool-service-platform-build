import pathlib
import subprocess
import sys

REPO = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts/phase37_step42_monitored_live_write_ops_no_write_dry_run_verification_planning_evidence_index_packet.ps1"
UI = REPO / "ui/pages/1858_Phase37_Step42_Monitored_Live_Write_Ops_No_Write_Dry_Run_Verification_Planning_Evidence_Index.py"
DOC = REPO / "docs/PHASE37_STEP42_MONITORED_LIVE_WRITE_OPS_NO_WRITE_DRY_RUN_VERIFICATION_PLANNING_EVIDENCE_INDEX_PACKET.md"
TEST = REPO / "tests/test_phase37_step42_monitored_live_write_ops_no_write_dry_run_verification_planning_evidence_index_packet.py"


def read(path: pathlib.Path) -> str:
    return path.read_text(encoding="utf-8")


def test_phase37_step_42_files_exist() -> None:
    for path in (SCRIPT, UI, DOC, TEST):
        assert path.exists(), f"Missing expected file: {path}"


def test_phase37_step_42_launcher_has_valid_param_block() -> None:
    text = read(SCRIPT)
    assert text.lstrip().startswith("param(")
    assert "[string]$RepoRoot" in text
    assert "[ValidateSet(" in text


def test_phase37_step_42_safety_markers_present() -> None:
    text = read(SCRIPT) + "\n" + read(UI) + "\n" + read(DOC)
    required = [
        "planning_only", "no_real_bridge_http_client", "no_network_transport_implementation",
        "no_bridge_post", "no_network_sockets", "phase37_execution_start",
        "phase37_implementation_start", "trusted_production_monitored_live_write_operations_start",
        "monitored_live_write_operations_start", "live_write_activation_start", "live_write_apply_start",
        "live_user_access_start", "no_live_user_access", "no_live_write_activation", "no_live_write_apply",
        "phase38_start", "phase38_boundary_creation", "live_write_disabled", "live_write_unarmed",
    ]
    for marker in required:
        assert marker in text


def test_phase37_step_42_forbidden_runtime_markers_not_enabled() -> None:
    compact = (read(SCRIPT) + "\n" + read(UI) + "\n" + read(DOC)).replace(" ", "").lower()
    forbidden_true = [
        "phase38_start=true", "phase38_boundary_creation=true", "phase37_execution_start=true",
        "phase37_implementation_start=true", "trusted_production_monitored_live_write_operations_start=true",
        "trusted_production_monitored_live_write_operations_execution_start=true", "monitored_live_write_operations_start=true",
        "monitored_live_write_operations_execution_start=true", "live_write_activation_start=true", "live_write_apply_start=true",
        "live_user_access_start=true", "no_live_user_access=false", "no_live_write_activation=false", "no_live_write_apply=false",
    ]
    for marker in forbidden_true:
        assert marker not in compact


def test_phase37_step_42_launcher_smoke_passes() -> None:
    result = subprocess.run(
        ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(SCRIPT), "-RepoRoot", str(REPO), "-Action", "smoke"],
        check=False, text=True, capture_output=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "SMOKE TEST PASS" in result.stdout


def test_phase37_step_42_ui_compiles() -> None:
    result = subprocess.run([sys.executable, "-m", "py_compile", str(UI)], check=False, text=True, capture_output=True)
    assert result.returncode == 0, result.stdout + result.stderr


def test_phase37_step_42_literal_pass_markers_present() -> None:
    text = read(SCRIPT)
    assert "APPLY PASS" in text
    assert "SMOKE TEST PASS" in text


def test_phase37_step_42_stays_inside_phase37() -> None:
    text = read(SCRIPT) + "\n" + read(UI) + "\n" + read(DOC)
    assert "Phase 37" in text
    assert "phase38_boundary_creation=false" in text or "phase38_boundary_creation = $false" in text
