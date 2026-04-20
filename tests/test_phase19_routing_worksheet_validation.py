from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def test_routing_worksheet_validator_script_is_validation_only() -> None:
    script = read("scripts/phase19_validate_routing_worksheet.ps1")
    assert "phase19_routing_worksheet_validation_" in script
    assert "validation_only = $true" in script
    assert "platform_db_mutation_performed = $false" in script
    assert "bridge_mutation_performed = $false" in script
    assert "bridge_post_called = $false" in script
    assert "lacrm_call_performed = $false" in script
    assert "routing_write_endpoint_implemented = $false" in script
    assert "invalid_operator_decision" in script
    assert "high_risk_approved" in script
    assert "auto_attach_without_contact" in script
    assert "Import-Csv" in script
    assert "Invoke-RestMethod" not in script
    assert "Remove-Item" not in script


def test_routing_worksheet_validator_streamlit_page_is_read_only() -> None:
    page = read("ui/pages/28_Routing_Worksheet_Validator.py")
    assert "Phase 19 Routing Worksheet Validator" in page
    assert "validation-only" in page.lower()
    assert "does not save routing rules" in page
    assert "does not call bridge POST endpoints" in page
    assert "does not call LACRM" in page
    assert "phase19_routing_worksheet_validation_*" in page
    assert "requests.get" not in page
    assert "requests.post" not in page
    assert "st.download_button" in page


def test_routing_worksheet_validator_docs_capture_boundaries() -> None:
    doc = read("docs/PHASE19_STEP26_ROUTING_WORKSHEET_VALIDATION.md")
    assert "validates the Step 25 routing approval worksheet" in doc
    assert "validation-only" in doc
    assert "does not save routing rules" in doc
    assert "does not mutate bridge state" in doc
    assert "does not call LACRM" in doc
    assert "Do not stage generated validation reports" in doc
