from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def test_routing_candidate_import_check_script_is_dry_run_only() -> None:
    script = read("scripts/phase19_check_routing_candidate_import.ps1")
    assert "phase19_routing_candidate_import_check_" in script
    assert "dry_run_check_only = $true" in script
    assert "platform_db_mutation_performed = $false" in script
    assert "bridge_mutation_performed = $false" in script
    assert "bridge_post_called = $false" in script
    assert "lacrm_call_performed = $false" in script
    assert "candidate_import_performed = $false" in script
    assert "candidate_import_enabled = $false" in script
    assert "routing_write_endpoint_implemented = $false" in script
    assert "would_create" in script
    assert "would_update" in script
    assert "would_skip_existing" in script
    assert "would_block" in script
    assert "Invoke-RestMethod" in script
    assert "Invoke-RestMethod -Method Post" not in script
    assert "Remove-Item" not in script


def test_routing_candidate_import_check_streamlit_page_is_read_only() -> None:
    page = read("ui/pages/32_Routing_Candidate_Import_Check.py")
    assert "Phase 19 Routing Candidate Import Check" in page
    assert "dry-run-check-only" in page.lower()
    assert "does not import candidates" in page
    assert "does not save routing rules" in page
    assert "does not call bridge POST endpoints" in page
    assert "does not call LACRM" in page
    assert "phase19_routing_candidate_import_check_*" in page
    assert "requests.get" not in page
    assert "requests.post" not in page
    assert "st.download_button" in page


def test_routing_candidate_import_check_docs_capture_boundaries() -> None:
    doc = read("docs/PHASE19_STEP30_ROUTING_CANDIDATE_IMPORT_CHECK.md")
    assert "dry-run checker only" in doc
    assert "does not import anything" in doc
    assert "does not mutate bridge state" in doc
    assert "does not call LACRM" in doc
    assert "Do not stage generated check reports" in doc
