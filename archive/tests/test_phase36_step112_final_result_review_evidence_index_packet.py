from __future__ import annotations

import pathlib
import subprocess
import sys

REPO = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts/phase36_step112_final_result_review_evidence_index_packet.ps1"
UI = REPO / "ui/pages/1808_Phase36_Step112_Live_Write_Expansion_Final_Result_Review_Evidence_Index.py"
DOC = REPO / "docs/PHASE36_STEP112_CONTROLLED_LIVE_WRITE_EXPANSION_FINAL_RESULT_REVIEW_EVIDENCE_INDEX_PACKET.md"
TEST = REPO / "tests/test_phase36_step112_final_result_review_evidence_index_packet.py"


def read(path: pathlib.Path) -> str:
    return path.read_text(encoding="utf-8")


def test_phase36_step_112_files_exist() -> None:
    for path in (SCRIPT, UI, DOC, TEST):
        assert path.exists(), f"missing expected file: {path}"


def test_phase36_step_112_launcher_has_required_safe_markers() -> None:
    text = read(SCRIPT)
    for marker in [
        "planning_only = $true",
        "no_real_bridge_http_client = $true",
        "no_network_transport_implementation = $true",
        "no_bridge_post = $true",
        "no_network_sockets = $true",
        "no_live_user_access = $true",
        "no_live_write_activation = $true",
        "no_live_write_apply = $true",
        "phase37_start = $false",
        "phase37_boundary_creation = $false",
        "lacrm_default_mode = \"dry_run\"",
        "live_write_disabled = $true",
        "live_write_unarmed = $true",
    ]:
        assert marker in text


def test_phase36_step_112_operational_files_do_not_enable_forbidden_markers() -> None:
    forbidden_keys = [
        "phase37_start",
        "phase37_boundary_creation",
        "phase36_execution_start",
        "phase36_implementation_start",
        "implementation_phase_start",
        "trusted_production_controlled_live_write_expansion_start",
        "trusted_production_controlled_live_write_expansion_execution_start",
        "controlled_live_write_expansion_start",
        "controlled_live_write_expansion_execution_start",
        "live_write_activation_start",
        "live_write_apply_start",
        "live_user_access_start",
        "network_transport_runtime_start",
        "bridge_transport_runtime_start",
    ]
    for path in (SCRIPT, UI, DOC):
        compact = read(path).replace(" ", "").replace("\n", "").lower()
        for key in forbidden_keys:
            assert (key.lower() + "=true") not in compact
            assert (key.lower() + "=$true") not in compact


def test_phase36_step_112_ui_and_doc_reference_dry_run_no_apply() -> None:
    text = read(UI) + "\n" + read(DOC)
    assert "lacrm_default_mode=dry_run" in text
    assert "no_live_write_activation=true" in text
    assert "no_live_write_apply=true" in text
    assert "phase37_start=false" in text


def test_phase36_step_112_launcher_apply_passes() -> None:
    result = subprocess.run(
        ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(SCRIPT), "-RepoRoot", str(REPO), "-Action", "apply"],
        check=False,
        text=True,
        capture_output=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "APPLY PASS" in result.stdout


def test_phase36_step_112_launcher_smoke_passes() -> None:
    result = subprocess.run(
        ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(SCRIPT), "-RepoRoot", str(REPO), "-Action", "smoke"],
        check=False,
        text=True,
        capture_output=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "SMOKE TEST PASS" in result.stdout


def test_phase36_step_112_ui_compiles() -> None:
    result = subprocess.run([sys.executable, "-m", "py_compile", str(UI)], check=False, text=True, capture_output=True)
    assert result.returncode == 0, result.stdout + result.stderr


def test_phase36_step_112_stays_inside_phase36() -> None:
    text = read(SCRIPT) + "\n" + read(UI) + "\n" + read(DOC)
    assert "Phase 36" in text
    assert "phase37_boundary_creation=false" in text or "phase37_boundary_creation = $false" in text

