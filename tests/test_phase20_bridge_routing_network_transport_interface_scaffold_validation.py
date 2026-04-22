from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def test_bridge_routing_network_transport_interface_scaffold_validation_script_is_get_only() -> None:
    script = read("scripts/phase20_validate_bridge_routing_network_transport_interface_scaffold.ps1")
    assert "phase20_bridge_routing_network_transport_interface_scaffold_validation_" in script
    assert "bridge_routing_network_transport_interface_scaffold_validation_only = $true" in script
    assert "bridge_get_only = $true" in script
    assert "platform_db_mutation_performed = $false" in script
    assert "bridge_mutation_performed = $false" in script
    assert "bridge_post_called = $false" in script
    assert "lacrm_call_performed = $false" in script
    assert "real_bridge_http_client_implemented = $false" in script
    assert "network_transport_implemented = $false" in script
    assert "network_transport_enabled = $false" in script
    assert "network_transport_armed = $false" in script
    assert "network_socket_opened = $false" in script
    assert "bridge_post_call_implemented = $false" in script
    assert "routing_write_endpoint_implemented = $false" in script
    assert "can_execute_bridge_write_now = $false" in script
    assert "can_add_network_transport_now = $false" in script
    assert "can_enable_network_transport_now = $false" in script
    assert "can_arm_network_transport_now = $false" in script
    assert "can_open_network_socket_now = $false" in script
    assert "can_add_real_bridge_http_client_now = $false" in script
    assert "can_add_bridge_post_now = $false" in script
    assert "phase20_bridge_routing_network_transport_interface_scaffold_*" in script
    assert "phase20_bridge_routing_network_transport_implementation_plan_*" in script
    assert "phase20_bridge_routing_network_transport_release_checkpoint_*" in script
    assert "BridgeRoutingTransportRequest" in script
    assert "BridgeRoutingTransportResult" in script
    assert "BridgeRoutingTransportAdapterInterface" in script
    assert "Invoke-RestMethod" in script
    assert "Invoke-RestMethod -Method Post" not in script
    assert "Remove-Item" not in script
    assert "ConvertTo-Json -Depth 120" not in script


def test_bridge_routing_network_transport_interface_scaffold_validation_streamlit_page_is_report_only() -> None:
    page = read("ui/pages/67_Bridge_Routing_Network_Transport_Interface_Scaffold_Validation.py")
    assert "Phase 20 Bridge Routing Network Transport Interface Scaffold Validation" in page
    assert "network-transport-interface-scaffold-validation-only" in page
    assert "does not write to the bridge" in page
    assert "does not call bridge POST endpoints" in page
    assert "does not open network sockets" in page
    assert "does not call LACRM" in page
    assert "phase20_bridge_routing_network_transport_interface_scaffold_validation_*" in page
    assert "phase20_bridge_routing_network_transport_interface_scaffold_validation.json" in page
    assert "requests.get" not in page
    assert "requests.post" not in page
    assert "st.download_button" in page


def test_bridge_routing_network_transport_interface_scaffold_validation_docs_capture_boundaries() -> None:
    doc = read("docs/PHASE20_STEP15_BRIDGE_ROUTING_NETWORK_TRANSPORT_INTERFACE_SCAFFOLD_VALIDATION.md")
    assert "validates the Phase 20 Step 14 bridge routing network transport interface scaffold" in doc
    assert "network-transport-interface-scaffold-validation-only" in doc
    assert "bridge GET only" in doc
    assert "does not mutate bridge state" in doc
    assert "does not call LACRM" in doc
    assert "Do not stage generated interface scaffold validation reports" in doc
