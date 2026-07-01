from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def test_routing_approval_worksheet_generator_is_worksheet_only() -> None:
    script = read("scripts/phase19_generate_routing_approval_worksheet.ps1")
    assert "phase19_routing_approval_worksheet_" in script
    assert "worksheet_only = $true" in script
    assert "platform_db_mutation_performed = $false" in script
    assert "bridge_mutation_performed = $false" in script
    assert "bridge_post_called = $false" in script
    assert "lacrm_call_performed = $false" in script
    assert "routing_write_endpoint_implemented = $false" in script
    assert "operator_decision = \"unreviewed\"" in script
    assert "Export-Csv" in script
    assert "Invoke-RestMethod" not in script
    assert "Remove-Item" not in script


def test_routing_approval_worksheet_streamlit_page_is_download_only() -> None:
    page = read("ui/pages/27_Routing_Approval_Worksheet.py")
    assert "Phase 19 Routing Approval Worksheet" in page
    assert "worksheet-only" in page.lower()
    assert "does not save routing rules" in page
    assert "does not call bridge POST endpoints" in page
    assert "does not call LACRM" in page
    assert "Download edited worksheet CSV" in page
    assert "st.data_editor" in page
    assert "requests.get" not in page
    assert "requests.post" not in page
    assert "st.download_button" in page


def test_routing_approval_worksheet_docs_capture_boundaries() -> None:
    doc = read("docs/PHASE19_STEP25_ROUTING_APPROVAL_WORKSHEET.md")
    assert "editable operator worksheet" in doc
    assert "download-only" in doc
    assert "does not save routing rules" in doc
    assert "does not mutate bridge state" in doc
    assert "does not call LACRM" in doc
    assert "Do not stage generated worksheets" in doc
