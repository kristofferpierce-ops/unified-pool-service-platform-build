import pathlib
import subprocess
import sys

REPO = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts/phase37_step12_monitored_live_write_ops_guardrail_evidence_index_packet.ps1"
UI = REPO / "ui/pages/1828_Phase37_Step12_Monitored_Live_Write_Ops_Guardrail_Evidence_Index.py"
DOC = REPO / "docs/PHASE37_STEP12_MONITORED_LIVE_WRITE_OPS_GUARDRAIL_EVIDENCE_INDEX_PACKET.md"
TEST = REPO / "tests/test_phase37_step12_monitored_live_write_ops_guardrail_evidence_index_packet.py"


def _read(path: pathlib.Path) -> str:
    return path.read_text(encoding="utf-8")


def test_phase37_step12_files_exist():
    assert SCRIPT.exists()
    assert UI.exists()
    assert DOC.exists()
    assert TEST.exists()


def test_phase37_step12_launcher_has_valid_param_block():
    text = _read(SCRIPT)
    assert text.lstrip().startswith("param(")
    assert '[string]$RepoRoot = ""' in text
    assert '[ValidateSet("status", "apply", "smoke", "packet", "all")]' in text


def test_phase37_step12_required_safety_markers_present():
    combined = "\n".join(_read(path) for path in (SCRIPT, UI, DOC))
    for marker in [
        "planning_only", "no_real_bridge_http_client", "no_network_transport_implementation",
        "no_bridge_post", "no_network_sockets", "phase37_execution_start",
        "phase37_implementation_start", "trusted_production_monitored_live_write_operations_start",
        "monitored_live_write_operations_start", "live_write_activation_start", "live_write_apply_start",
        "live_user_access_start", "no_live_user_access", "no_live_write_activation", "no_live_write_apply",
        "phase38_start", "phase38_boundary_creation", "live_write_disabled", "live_write_unarmed",
    ]:
        assert marker in combined


def test_phase37_step12_forbidden_true_markers_absent():
    combined = "\n".join(_read(path) for path in (SCRIPT, UI, DOC)).lower().replace(" ", "")
    for marker in [
        "phase38_start=true", "phase38_boundary_creation=true", "phase37_execution_start=true",
        "phase37_implementation_start=true", "trusted_production_monitored_live_write_operations_start=true",
        "trusted_production_monitored_live_write_operations_execution_start=true",
        "monitored_live_write_operations_start=true", "monitored_live_write_operations_execution_start=true",
        "live_write_activation_start=true", "live_write_apply_start=true", "live_user_access_start=true",
        "no_live_user_access=false", "no_live_write_activation=false", "no_live_write_apply=false",
    ]:
        assert marker not in combined


def test_phase37_step12_literal_pass_markers_present():
    text = _read(SCRIPT)
    assert "APPLY PASS" in text
    assert "SMOKE TEST PASS" in text


def test_phase37_step12_launcher_smoke_passes():
    result = subprocess.run(
        ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(SCRIPT), "-RepoRoot", str(REPO), "-Action", "smoke"],
        check=False,
        text=True,
        capture_output=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "SMOKE TEST PASS" in result.stdout


def test_phase37_step12_ui_compiles():
    result = subprocess.run([sys.executable, "-m", "py_compile", str(UI)], check=False, text=True, capture_output=True)
    assert result.returncode == 0, result.stdout + result.stderr


def test_phase37_step12_doc_records_no_runtime_boundary():
    text = _read(DOC)
    assert "No server launch" in text
    assert "No Phase 38 boundary creation" in text
    assert "phase38_boundary_creation=false" in text
