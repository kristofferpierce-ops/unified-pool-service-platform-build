import pathlib
import py_compile
import subprocess

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/p39_s007_activation_gate_readiness_approval_readiness.ps1"
UI = ROOT / "ui/pages/2063_Phase39_Step7_Activation_Gate_Readiness_Approval_Readiness.py"
DOC = ROOT / "docs/P39_S007_ACTIVATION_GATE_READINESS_APPROVAL_READINESS.md"


def read(path: pathlib.Path) -> str:
    return path.read_text(encoding="utf-8")


def compact_text(*paths: pathlib.Path) -> str:
    return "\n".join(read(path) for path in paths).replace(" ", "").lower()


def test_phase39_step_7_files_exist() -> None:
    assert SCRIPT.exists()
    assert UI.exists()
    assert DOC.exists()


def test_phase39_step_7_launcher_has_valid_param_block() -> None:
    text = read(SCRIPT)
    assert text.startswith("param(")


def test_phase39_step_7_launcher_runs_all() -> None:
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
    assert "phase40_start=false" in output
    assert "phase40_boundary_creation=false" in output


def test_phase39_step_7_ui_compiles() -> None:
    py_compile.compile(str(UI), doraise=True)


def test_phase39_step_7_doc_has_required_safe_markers() -> None:
    compact = read(DOC).replace(" ", "").lower()
    required = [
        "planning_only=true",
        "no_live_user_access=true",
        "no_live_write_activation=true",
        "no_live_write_apply=true",
        "live_write_disabled=true",
        "live_write_unarmed=true",
        "phase40_start=false",
        "phase40_boundary_creation=false",
    ]
    for marker in required:
        assert marker in compact


def test_phase39_step_7_forbidden_runtime_markers_not_enabled() -> None:
    compact = compact_text(SCRIPT, UI, DOC)
    forbidden_true = [
        "phase40_start=true",
        "phase40_boundary_creation=true",
        "phase39_execution_start=true",
        "phase39_implementation_start=true",
        "implementation_phase_start=true",
        "trusted_production_live_write_activation_gate_start=true",
        "trusted_production_live_write_activation_gate_execution_start=true",
        "live_write_activation_gate_start=true",
        "live_write_activation_gate_execution_start=true",
        "live_write_activation_start=true",
        "live_write_apply_start=true",
        "live_user_access_start=true",
        "no_live_user_access=false",
        "no_live_write_activation=false",
        "no_live_write_apply=false",
    ]
    for marker in forbidden_true:
        assert marker not in compact


def test_phase39_step_7_no_phase40_files_created_by_payload() -> None:
    assert "phase40" in read(SCRIPT).lower()
    assert "phase40_start=false" in read(DOC).replace(" ", "").lower()
    matches = [
        item
        for folder in ["scripts", "docs", "tests", "ui/pages"]
        for item in (ROOT / folder).glob("*phase40*")
    ]
    assert not matches


def test_phase39_step_7_literal_pass_markers_present() -> None:
    text = read(SCRIPT)
    assert "APPLY PASS" in text
    assert "SMOKE TEST PASS" in text