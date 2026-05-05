from pathlib import Path
import py_compile

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts" / "kps_ui_stabilization_pass1_launcher.ps1"
PAGE = REPO / "ui" / "pages" / "000_KPS_UI_Stabilization_Pass1.py"
DOC = REPO / "docs" / "KPS_UI_STABILIZATION_PASS1.md"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


def test_stabilization_files_exist():
    assert SCRIPT.exists()
    assert PAGE.exists()
    assert DOC.exists()


def test_launcher_actions_and_no_exit():
    text = read(SCRIPT)
    assert 'ValidateSet("status", "audit", "launch", "stop", "all")' in text
    assert "Start-KpsLocalProgram" in text
    assert "Stop-KpsLocalAppListeners" in text
    assert "Write-KpsAuditReport" in text
    assert "exit 0" not in text.lower()


def test_launcher_safe_environment_markers():
    text = read(SCRIPT)
    assert 'LACRM_DEFAULT_MODE = "dry_run"' in text
    assert 'LACRM_LIVE_WRITE = "false"' in text
    assert 'LIVE_WRITE_DISABLED = "true"' in text
    assert 'LIVE_WRITE_UNARMED = "true"' in text
    assert 'NO_BRIDGE_POST = "true"' in text
    assert 'NO_NETWORK_TRANSPORT_IMPLEMENTATION = "true"' in text
    assert 'NO_NETWORK_SOCKETS = "true"' in text


def test_launcher_avoids_known_powershell_parser_traps():
    text = read(SCRIPT)
    assert "$File:" not in text
    assert "$Retries:" not in text
    assert "Join-Path $Repo @(" not in text
    assert "Join-Path $RepoRoot @(" not in text


def test_launcher_uses_venv_proof_and_expected_ports():
    text = read(SCRIPT)
    assert "SYS_EXECUTABLE=" in text
    assert "SYS_PREFIX=" in text
    assert "app.api.main" in text
    assert "--port 8000" in text
    assert "--server.port 8501" in text


def test_streamlit_page_compiles():
    py_compile.compile(str(PAGE), doraise=True)


def test_doc_mentions_debug_priority_and_no_live_write():
    text = read(DOC)
    assert "Debug real workflow pages first" in text
    assert "LIVE_WRITE_DISABLED=true" in text
    assert "NO_BRIDGE_POST=true" in text
    assert "NO_NETWORK_TRANSPORT_IMPLEMENTATION=true" in text

