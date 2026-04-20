from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def test_repair_script_hard_checks_recurring_dependencies() -> None:
    script = read("scripts/phase19_repair_platform_venv.ps1")
    assert "pydantic_core._pydantic_core" in script
    assert "httpx" in script
    assert "from app.api.main import app" in script
    assert "--force-reinstall" in script
    assert "--no-cache-dir" in script
    assert "deactivate" not in script.lower()


def test_stack_scripts_preserve_port_contract() -> None:
    start_script = read("scripts/phase19_start_local_stack.ps1")
    verify_script = read("scripts/phase19_verify_local_stack.ps1")
    stop_script = read("scripts/phase19_stop_local_stack.ps1")
    for expected in ["8010", "8501", "8000"]:
        assert expected in start_script
        assert expected in verify_script
        assert expected in stop_script
    assert "ui\\Dashboard.py" in start_script
    assert "Keys Pool Service Data Hub" in verify_script


def test_environment_health_streamlit_page_is_read_only_and_labels_apps() -> None:
    page = read("ui/pages/17_Environment_Health.py")
    assert "Phase 19 Environment Health" in page
    assert "Streamlit dashboard on 8501" in page
    assert "FastAPI backend on 8010" in page
    assert "KPS Bridge / Data Hub UI on 8000" in page
    assert "phase19_repair_platform_venv.ps1" in page
    assert "requests.get" in page
    assert "requests.post" not in page
