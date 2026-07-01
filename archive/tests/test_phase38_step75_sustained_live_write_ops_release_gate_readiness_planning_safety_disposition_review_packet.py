import pathlib
import subprocess
import sys

REPO = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts/phase38_step75_sustained_live_write_ops_release_gate_readiness_planning_safety_disposition_review_packet.ps1"
UI = REPO / "ui/pages/2011_Phase38_Step75_Sustained_Live_Write_Ops_Release_Gate_Readiness_Safety_Review.py"
DOC = REPO / "docs/PHASE38_STEP75_SUSTAINED_LIVE_WRITE_OPS_RELEASE_GATE_READINESS_PLANNING_SAFETY_DISPOSITION_REVIEW_PACKET.md"
TEST = REPO / "tests/test_phase38_step75_sustained_live_write_ops_release_gate_readiness_planning_safety_disposition_review_packet.py"


def read(path: pathlib.Path) -> str:
    return path.read_text(encoding="utf-8")


def test_phase38_step_75_files_exist() -> None:
    for path in (SCRIPT, UI, DOC, TEST):
        assert path.exists(), f"Missing expected file: {path}"


def test_phase38_step_75_launcher_has_valid_param_block() -> None:
    text = read(SCRIPT)
    assert text.lstrip().startswith("param(")
    assert "[string]$RepoRoot" in text
    assert "[ValidateSet(" in text


def test_phase38_step_75_payloads_are_bom_free() -> None:
    for path in (SCRIPT, UI, DOC, TEST):
        assert not path.read_bytes().startswith(b"\xef\xbb\xbf"), f"BOM detected in {path}"


def test_phase38_step_75_safety_markers_present() -> None:
    text = read(SCRIPT) + "\n" + read(UI) + "\n" + read(DOC)
    required = [
        "planning_only=true",
        "no_real_bridge_http_client=true",
        "no_network_transport_implementation=true",
        "no_bridge_post=true",
        "no_network_sockets=true",
        "phase38_execution_start=false",
        "phase38_implementation_start=false",
        "implementation_phase_start=false",
        "trusted_production_sustained_live_write_operations_start=false",
        "trusted_production_sustained_live_write_operations_execution_start=false",
        "sustained_live_write_operations_start=false",
        "sustained_live_write_operations_execution_start=false",
        "live_write_activation_start=false",
        "live_write_apply_start=false",
        "live_user_access_start=false",
        "no_live_user_access=true",
        "no_live_write_activation=true",
        "no_live_write_apply=true",
        "phase39_start=false",
        "phase39_boundary_creation=false",
        "lacrm_default_mode=dry_run",
        "live_write_disabled=true",
        "live_write_unarmed=true",
    ]
    for marker in required:
        assert marker in text


def test_phase38_step_75_forbidden_runtime_markers_not_enabled() -> None:
    compact = (read(SCRIPT) + "\n" + read(UI) + "\n" + read(DOC)).replace(" ", "").lower()
    forbidden_true = [
        "phase39_start=true",
        "phase39_boundary_creation=true",
        "phase38_execution_start=true",
        "phase38_implementation_start=true",
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


def test_phase38_step_75_launcher_smoke_passes() -> None:
    result = subprocess.run(
        ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(SCRIPT), "-RepoRoot", str(REPO), "-Action", "smoke"],
        check=False,
        text=True,
        capture_output=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "SMOKE TEST PASS" in result.stdout


def test_phase38_step_75_ui_compiles() -> None:
    result = subprocess.run([sys.executable, "-m", "py_compile", str(UI)], check=False, text=True, capture_output=True)
    assert result.returncode == 0, result.stdout + result.stderr


def test_phase38_step_75_literal_pass_markers_present() -> None:
    text = read(SCRIPT)
    assert "APPLY PASS" in text
    assert "SMOKE TEST PASS" in text


def test_phase38_step_75_stays_inside_phase38() -> None:
    text = read(SCRIPT) + "\n" + read(UI) + "\n" + read(DOC)
    assert "Phase 38" in text
    assert "phase39_boundary_creation=false" in text or "phase39_boundary_creation = $false" in text