from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def test_bridge_routing_write_contract_script_is_contract_only() -> None:
    script = read("scripts/phase19_generate_bridge_routing_write_contract.ps1")
    assert "phase19_bridge_routing_write_contract_" in script
    assert "bridge_routing_write_contract_only = $true" in script
    assert "platform_db_mutation_performed = $false" in script
    assert "bridge_mutation_performed = $false" in script
    assert "bridge_post_called = $false" in script
    assert "lacrm_call_performed = $false" in script
    assert "bridge_write_endpoint_implemented = $false" in script
    assert "routingRuleSummary" in script
    assert "setManualBtn" in script
    assert "/api/routing-rules" in script
    assert "expected_payload_fields" in script
    assert "Invoke-RestMethod" in script
    assert "Invoke-RestMethod -Method Post" not in script
    assert "Remove-Item" not in script


def test_bridge_routing_write_contract_streamlit_page_is_report_only() -> None:
    page = read("ui/pages/38_Bridge_Routing_Write_Contract.py")
    assert "Phase 19 Bridge Routing Write Contract" in page
    assert "contract-only" in page.lower()
    assert "does not write to the bridge" in page
    assert "does not call bridge POST endpoints" in page
    assert "does not call LACRM" in page
    assert "phase19_bridge_routing_write_contract_*" in page
    assert "requests.get" not in page
    assert "requests.post" not in page
    assert "st.download_button" in page


def test_bridge_routing_write_contract_docs_capture_boundaries() -> None:
    doc = read("docs/PHASE19_STEP36_BRIDGE_ROUTING_WRITE_CONTRACT.md")
    assert "read-only bridge routing write contract" in doc
    assert "does not call the bridge write endpoint" in doc
    assert "contract-only" in doc
    assert "does not mutate bridge state" in doc
    assert "does not call LACRM" in doc
    assert "Do not stage generated contract reports" in doc
