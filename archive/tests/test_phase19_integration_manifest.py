from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def test_manifest_generator_is_read_only_and_covers_three_repos() -> None:
    script = read("scripts/phase19_generate_integration_manifest.ps1")
    assert "phase19_integration_manifest_" in script
    assert "front_desk_bridge_repo" in script
    assert "start_here_extractor_m1_completion" in script
    assert "unified_pool_service_platform_build" in script
    assert "Keys Pool Service Data Hub" in script
    assert "live_lacrm_apply_allowed = $false" in script
    assert "Invoke-RestMethod" in script
    assert "Invoke-RestMethod -Method Post" not in script
    assert "Remove-Item" not in script


def test_manifest_streamlit_page_reads_generated_files_only() -> None:
    page = read("ui/pages/20_Integration_Manifest.py")
    assert "Phase 19 Integration Manifest" in page
    assert "phase19_integration_manifest_*.json" in page
    assert "does not call LACRM" in page
    assert "does not mutate platform data" in page
    assert "front_desk_bridge_repo" in page
    assert "data/unified_pool_service_platform.db" in page
    assert "requests.get" not in page
    assert "requests.post" not in page
    assert "st.download_button" in page


def test_manifest_docs_capture_app_map_and_commit_guardrails() -> None:
    doc = read("docs/PHASE19_STEP18_INTEGRATION_MANIFEST.md")
    assert "8501" in doc and "8010" in doc and "8000" in doc
    assert "original KPS Bridge / Data Hub UI" in doc
    assert "Do not stage local databases" in doc
    assert "generated backups" in doc
