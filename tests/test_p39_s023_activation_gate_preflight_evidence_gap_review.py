from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/p39_s023_activation_gate_preflight_evidence_gap_review.ps1"
UI = ROOT / "ui/pages/2079_Phase39_Step23_Activation_Gate_Preflight_Evidence_Gap_Review.py"
DOC = ROOT / "docs/P39_S023_ACTIVATION_GATE_PREFLIGHT_EVIDENCE_GAP_REVIEW.md"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_phase39_step_23_files_exist() -> None:
    assert SCRIPT.exists()
    assert UI.exists()
    assert DOC.exists()


def test_phase39_step_23_launcher_has_valid_param_block() -> None:
    assert read(SCRIPT).lstrip().startswith("param(")


def test_phase39_step_23_safety_markers_present() -> None:
    combined = "\n".join([read(SCRIPT), read(UI), read(DOC)]).replace(" ", "").lower()
    required = [
        "planning_only=true",
        "no_real_bridge_http_client=true",
        "no_network_transport_implementation=true",
        "no_bridge_post=true",
        "no_network_sockets=true",
        "phase39_execution_start=false",
        "phase39_implementation_start=false",
        "trusted_production_live_write_activation_gate_start=false",
        "trusted_production_live_write_activation_gate_execution_start=false",
        "live_write_activation_gate_start=false",
        "live_write_activation_gate_execution_start=false",
        "live_write_activation_start=false",
        "live_write_apply_start=false",
        "live_user_access_start=false",
        "no_live_user_access=true",
        "no_live_write_activation=true",
        "no_live_write_apply=true",
        "phase40_start=false",
        "phase40_boundary_creation=false",
        "lacrm_default_mode=dry_run",
        "live_write_disabled=true",
        "live_write_unarmed=true",
    ]
    for marker in required:
        assert marker in combined


def test_phase39_step_23_forbidden_runtime_markers_not_enabled() -> None:
    compact = (read(SCRIPT) + "\n" + read(UI) + "\n" + read(DOC)).replace(" ", "").lower()
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


def is_true_phase40_artifact(path: Path) -> bool:
    name = path.name.lower()
    return (
        name.startswith("phase40_")
        or name.startswith("phase40-")
        or name.startswith("p40_")
        or name.startswith("p40-")
        or name.startswith("test_phase40")
        or name.startswith("test_p40_")
        or "_phase40_" in name
        or "-phase40-" in name
    )


def test_phase39_step_23_no_phase40_files_created_by_payload() -> None:
    assert "phase40" in read(SCRIPT).lower()
    assert "phase40_start=false" in read(DOC).replace(" ", "").lower()
    assert not any(
        item
        for folder in ["scripts", "docs", "tests", "ui/pages"]
        for item in (ROOT / folder).glob("*")
        if is_true_phase40_artifact(item)
    )


def test_phase39_step_23_launcher_smoke_passes() -> None:
    completed = subprocess.run(
        ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(SCRIPT), "-RepoRoot", str(ROOT), "-Action", "all"],
        check=True,
        capture_output=True,
        text=True,
    )
    assert "APPLY PASS" in completed.stdout
    assert "SMOKE TEST PASS" in completed.stdout


def test_phase39_step_23_ui_is_planning_only() -> None:
    text = read(UI)
    assert "Planning-only" in text or "planning-only" in text
    assert "no_live_write_apply" in text
    assert "phase40_boundary_creation" in text


def test_phase39_step_23_doc_records_activation_gate_hold() -> None:
    text = read(DOC).lower()
    assert "live-write activation gate remains unarmed" in text
    assert "phase40_boundary_creation=false" in text.replace(" ", "")


def test_phase39_step_23_no_server_or_transport_runtime() -> None:
    combined = "\n".join([read(SCRIPT), read(UI), read(DOC)]).lower()
    blocked = ["streamlit run", "uvicorn", "requests.post", "socket.", "websocket", "httpx.post"]
    for needle in blocked:
        assert needle not in combined