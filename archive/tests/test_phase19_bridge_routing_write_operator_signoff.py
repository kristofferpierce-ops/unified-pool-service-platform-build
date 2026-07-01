from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def test_bridge_routing_write_operator_signoff_script_is_get_only() -> None:
    script = read("scripts/phase19_generate_bridge_routing_write_operator_signoff.ps1")
    assert "phase19_bridge_routing_write_operator_signoff_" in script
    assert "bridge_routing_write_operator_signoff_only = $true" in script
    assert "bridge_get_only = $true" in script
    assert "platform_db_mutation_performed = $false" in script
    assert "bridge_mutation_performed = $false" in script
    assert "bridge_post_called = $false" in script
    assert "lacrm_call_performed = $false" in script
    assert "bridge_http_client_implemented = $false" in script
    assert "bridge_post_call_implemented = $false" in script
    assert "routing_write_endpoint_implemented = $false" in script
    assert "can_execute_bridge_write_now = $false" in script
    assert "can_add_bridge_http_client_now = $false" in script
    assert "approved_for_live_bridge_write = $false" in script
    assert "phase19_bridge_routing_write_preflight_matrix_*" in script
    assert "phase19_bridge_routing_write_cutover_packet_*" in script
    assert "operator_attestation" in script
    assert "Invoke-RestMethod" in script
    assert "Invoke-RestMethod -Method Post" not in script
    assert "Remove-Item" not in script
    assert "ConvertTo-Json -Depth 120" not in script


def test_bridge_routing_write_operator_signoff_streamlit_page_is_report_only() -> None:
    page = read("ui/pages/51_Bridge_Routing_Write_Operator_Signoff.py")
    assert "Phase 19 Bridge Routing Write Operator Signoff" in page
    assert "operator-signoff-only" in page.lower()
    assert "does not write to the bridge" in page
    assert "does not call bridge POST endpoints" in page
    assert "does not add a bridge HTTP client" in page
    assert "does not call LACRM" in page
    assert "phase19_bridge_routing_write_operator_signoff_*" in page
    assert "phase19_bridge_routing_write_operator_signoff.json" in page
    assert "requests.get" not in page
    assert "requests.post" not in page
    assert "st.download_button" in page


def test_bridge_routing_write_operator_signoff_docs_capture_boundaries() -> None:
    doc = read("docs/PHASE19_STEP49_BRIDGE_ROUTING_WRITE_OPERATOR_SIGNOFF.md")
    assert "operator signoff dossier" in doc
    assert "does not authorize live bridge routing writes" in doc
    assert "operator-signoff-only" in doc
    assert "bridge GET only" in doc
    assert "does not mutate bridge state" in doc
    assert "does not call LACRM" in doc
    assert "Do not stage generated operator signoff reports" in doc
