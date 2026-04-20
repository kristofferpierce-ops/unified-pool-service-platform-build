from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def test_release_checkpoint_streamlit_page_is_read_only_and_labels_apps() -> None:
    page = read("ui/pages/18_Release_Checkpoint.py")
    assert "Phase 19 Release Checkpoint" in page
    assert "Streamlit dashboard on 8501" in page
    assert "FastAPI backend/API on 8010" in page
    assert "original KPS Bridge / Data Hub UI on 8000" in page
    assert "requests.get" in page
    assert "requests.post" not in page
    assert "Live LACRM writes" in page
    assert "front_desk_bridge_repo" in page
    assert "data/unified_pool_service_platform.db" in page


def test_release_checkpoint_export_script_checks_runtime_without_mutation() -> None:
    script = read("scripts/phase19_export_release_checkpoint.ps1")
    assert "Invoke-RestMethod" in script
    assert "/health" in script
    assert "/connectors/ringcentral/ingestion-status" in script
    assert "/front-desk/lacrm-apply/status" in script
    assert "Keys Pool Service Data Hub" in script
    assert "front_desk_bridge_repo" in script
    assert "commit_database = $false" in script
    assert "live_lacrm_apply_allowed = $false" in script
    assert "Invoke-RestMethod -Method Post" not in script
    assert "requests.post" not in script


def test_release_checkpoint_docs_include_commit_guardrails() -> None:
    doc = read("docs/PHASE19_STEP15_RELEASE_CHECKPOINT.md")
    assert "read-only" in doc.lower()
    assert "Do not stage local databases" in doc
    assert "8501" in doc and "8010" in doc and "8000" in doc
