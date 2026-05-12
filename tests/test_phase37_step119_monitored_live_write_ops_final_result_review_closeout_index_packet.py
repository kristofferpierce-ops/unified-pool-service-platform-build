from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/phase37_step119_monitored_live_write_ops_final_result_review_closeout_index_packet.ps1"
UI = ROOT / "ui/pages/1935_Phase37_Step119_Monitored_Live_Write_Ops_Final_Result_Review_Closeout_Index.py"
DOC = ROOT / "docs/PHASE37_STEP119_MONITORED_LIVE_WRITE_OPS_FINAL_RESULT_REVIEW_CLOSEOUT_INDEX_PACKET.md"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_phase37_step_119_files_exist() -> None:
    assert SCRIPT.exists()
    assert UI.exists()
    assert DOC.exists()


def test_phase37_step_119_launcher_has_valid_param_block() -> None:
    assert read(SCRIPT).lstrip().startswith("param(")


def test_phase37_step_119_payloads_are_bom_free() -> None:
    for path in [SCRIPT, UI, DOC]:
        data = path.read_bytes()
        assert not data.startswith(b"\xef\xbb\xbf")


def test_phase37_step_119_safe_markers_present() -> None:
    combined = (read(SCRIPT) + "\n" + read(UI) + "\n" + read(DOC)).replace(" ", "").lower()
    expected = [
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
    for marker in expected:
        assert marker.replace(" ", "").lower() in combined


def test_phase37_step_119_forbidden_runtime_markers_not_enabled() -> None:
    compact = (read(SCRIPT) + "\n" + read(UI) + "\n" + read(DOC)).replace(" ", "").lower()
    forbidden_true = [
        "phase38_start=true",
        "phase38_boundary_creation=true",
        "phase37_execution_start=true",
        "phase37_implementation_start=true",
        "implementation_phase_start=true",
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


def test_phase37_step_119_no_phase38_files_created_by_payload() -> None:
    assert "phase38" in read(SCRIPT).lower()
    assert "phase38_start=false" in read(DOC).replace(" ", "").lower()
    hits = []
    for folder in ["scripts", "docs", "tests", "ui/pages"]:
        hits.extend((ROOT / folder).glob("*phase38*"))
    assert not hits


def test_phase37_step_119_launcher_smoke_passes() -> None:
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
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "APPLY PASS" in result.stdout
    assert "SMOKE TEST PASS" in result.stdout


def test_phase37_step_119_ui_is_short_named() -> None:
    assert len(str(UI.relative_to(ROOT)).replace("\\\\", "/")) < 130