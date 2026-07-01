import pathlib
import py_compile
import subprocess

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/phase38_step99_sustained_live_write_ops_final_release_hold_closeout_index_packet.ps1"
UI = ROOT / "ui/pages/2035_Phase38_Step99_Sustained_Live_Write_Ops_Final_Release_Hold_Closeout_Index.py"
DOC = ROOT / "docs/PHASE38_STEP99_SUSTAINED_LIVE_WRITE_OPS_FINAL_RELEASE_HOLD_CLOSEOUT_INDEX_PACKET.md"


def read(path: pathlib.Path) -> str:
    return path.read_text(encoding="utf-8")


def compact_text(*paths: pathlib.Path) -> str:
    return "\n".join(read(path) for path in paths).replace(" ", "").lower()


def test_phase38_step_99_files_exist() -> None:
    assert SCRIPT.exists()
    assert UI.exists()
    assert DOC.exists()


def test_phase38_step_99_launcher_has_valid_param_block() -> None:
    text = read(SCRIPT)
    assert text.startswith("param(")


def test_phase38_step_99_launcher_runs_all() -> None:
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
        check=True,
        capture_output=True,
        text=True,
    )
    output = result.stdout
    assert "APPLY PASS" in output
    assert "SMOKE TEST PASS" in output
    assert "planning_only=true" in output
    assert "phase39_start=false" in output
    assert "phase39_boundary_creation=false" in output


def test_phase38_step_99_ui_compiles() -> None:
    py_compile.compile(str(UI), doraise=True)


def test_phase38_step_99_doc_has_required_safe_markers() -> None:
    compact = read(DOC).replace(" ", "").lower()
    required = [
        "planning_only=true",
        "no_live_user_access=true",
        "no_live_write_activation=true",
        "no_live_write_apply=true",
        "live_write_disabled=true",
        "live_write_unarmed=true",
        "phase39_start=false",
        "phase39_boundary_creation=false",
    ]
    for marker in required:
        assert marker in compact


def test_phase38_step_99_forbidden_runtime_markers_not_enabled() -> None:
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


def test_phase38_step_99_no_phase39_files_created_by_payload() -> None:
    assert "phase39" in read(SCRIPT).lower()
    assert "phase39_start=false" in read(DOC).replace(" ", "").lower()
    matches = [
        item
        for folder in ["scripts", "docs", "tests", "ui/pages"]
        for item in (ROOT / folder).glob("*phase39*")
    ]
    assert not matches


def test_phase38_step_99_literal_pass_markers_present() -> None:
    text = read(SCRIPT)
    assert "APPLY PASS" in text
    assert "SMOKE TEST PASS" in text