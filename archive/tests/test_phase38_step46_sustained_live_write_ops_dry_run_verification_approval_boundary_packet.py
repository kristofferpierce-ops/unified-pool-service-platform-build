from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'scripts/phase38_step46_sustained_live_write_ops_dry_run_verification_approval_boundary_packet.ps1'
UI = ROOT / 'ui/pages/1982_Phase38_Step46_Sustained_Live_Write_Ops_Dry_Run_Verification_Approval_Boundary.py'
DOC = ROOT / 'docs/PHASE38_STEP46_SUSTAINED_LIVE_WRITE_OPS_DRY_RUN_VERIFICATION_APPROVAL_BOUNDARY_PACKET.md'
TEST = ROOT / 'tests/test_phase38_step46_sustained_live_write_ops_dry_run_verification_approval_boundary_packet.py'


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def compact_text(*paths: Path) -> str:
    combined = "\n".join(read(path) for path in paths)
    return combined.replace(" ", "").lower()


def test_phase38_step46_files_exist() -> None:
    for path in [SCRIPT, UI, DOC, TEST]:
        assert path.exists(), path


def test_phase38_step46_launcher_has_valid_param_block() -> None:
    text = read(SCRIPT)
    assert text.lstrip().startswith("param(")
    assert "\ufeff" not in text[:1]


def test_phase38_step46_launcher_runs_all() -> None:
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
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    output = result.stdout + result.stderr
    assert "APPLY PASS" in output
    assert "SMOKE TEST PASS" in output


def test_phase38_step46_ui_compiles() -> None:
    compile(read(UI), str(UI), "exec")


def test_phase38_step46_doc_has_phase_and_step() -> None:
    text = read(DOC)
    assert "Phase: 38" in text
    assert "Step: 46" in text
    assert "phase39_start=false" in text.replace(" ", "").lower()


def test_phase38_step46_forbidden_runtime_markers_not_enabled() -> None:
    compact = compact_text(SCRIPT, UI, DOC)
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


def test_phase38_step46_required_safe_markers_present() -> None:
    compact = compact_text(SCRIPT, UI, DOC)
    required = [
        "planning_only=true",
        "no_real_bridge_http_client=true",
        "no_network_transport_implementation=true",
        "no_bridge_post=true",
        "no_network_sockets=true",
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
        assert marker in compact


def test_phase38_step46_no_phase39_files_created_by_payload() -> None:
    assert "phase39" in read(SCRIPT).lower()
    assert "phase39_start=false" in read(DOC).replace(" ", "").lower()
    assert not any(
        path
        for folder in ["scripts", "docs", "tests", "ui/pages"]
        for path in (ROOT / folder).glob("*phase39*")
    )