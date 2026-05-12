import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/phase38_step40_sustained_live_write_ops_no_write_dry_run_readiness_final_boundary_packet.ps1"
UI = ROOT / "ui/pages/1976_Phase38_Step40_Sustained_Live_Write_Ops_No_Write_Dry_Run_Readiness_Final_Boundary.py"
DOC = ROOT / "docs/PHASE38_STEP40_SUSTAINED_LIVE_WRITE_OPS_NO_WRITE_DRY_RUN_READINESS_FINAL_BOUNDARY_PACKET.md"
TEST = ROOT / "tests/test_phase38_step40_sustained_live_write_ops_no_write_dry_run_readiness_final_boundary_packet.py"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_phase38_step_40_files_exist() -> None:
    assert SCRIPT.exists()
    assert UI.exists()
    assert DOC.exists()
    assert TEST.exists()


def test_phase38_step_40_launcher_has_valid_param_block() -> None:
    text = read(SCRIPT)
    assert text.startswith("param(")
    assert not text.startswith("\ufeff")


def test_phase38_step_40_launcher_runs_all() -> None:
    result = subprocess.run(
        [
            "powershell.exe",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(SCRIPT),
            "-RepoRoot",
            str(ROOT),
            "-Action",
            "all",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "APPLY PASS" in result.stdout
    assert "SMOKE TEST PASS" in result.stdout


def test_phase38_step_40_safety_markers_present() -> None:
    combined = "\n".join([read(SCRIPT), read(UI), read(DOC)]).replace(" ", "").lower()
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
        assert marker in combined


def test_phase38_step_40_forbidden_runtime_markers_not_enabled() -> None:
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


def test_phase38_step_40_no_phase39_files_created_by_payload() -> None:
    assert "phase39" in read(SCRIPT).lower()
    assert "phase39_start=false" in read(DOC).replace(" ", "").lower()
    assert not any(any((ROOT / folder).glob("*phase39*")) for folder in ["scripts", "docs", "tests", "ui/pages"])


def test_phase38_step_40_ui_page_is_short_named_and_safe() -> None:
    assert len(str(UI.relative_to(ROOT))) < 150
    text = read(UI)
    assert "No live writes" in text or "no live writes" in text
    assert "phase39_boundary_creation" in text


def test_phase38_step_40_doc_names_four_file_packet() -> None:
    text = read(DOC)
    assert "scripts/phase38_step40_sustained_live_write_ops_no_write_dry_run_readiness_final_boundary_packet.ps1" in text
    assert "ui/pages/1976_Phase38_Step40_Sustained_Live_Write_Ops_No_Write_Dry_Run_Readiness_Final_Boundary.py" in text
    assert "docs/PHASE38_STEP40_SUSTAINED_LIVE_WRITE_OPS_NO_WRITE_DRY_RUN_READINESS_FINAL_BOUNDARY_PACKET.md" in text
    assert "tests/test_phase38_step40_sustained_live_write_ops_no_write_dry_run_readiness_final_boundary_packet.py" in text
