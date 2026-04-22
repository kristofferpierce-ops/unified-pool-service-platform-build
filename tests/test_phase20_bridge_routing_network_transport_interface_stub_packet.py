from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def test_interface_stub_module_is_non_network_and_importable() -> None:
    from app.services.routing_bridge_network_transport_contract_schema import build_sample_contract_packet
    from app.services.routing_bridge_network_transport_interface_stub import (
        BridgeRoutingNetworkTransportInterfaceStub,
        BridgeRoutingNetworkTransportNotImplemented,
        bridge_routing_network_transport_interface_stub_packet_dict,
        bridge_routing_network_transport_interface_stub_status,
        build_bridge_routing_network_transport_interface_stub,
    )

    status = bridge_routing_network_transport_interface_stub_status()
    assert status["interface_stub_scaffold_only"] is True
    assert status["non_network_interface_stub_created"] is True
    assert status["execution_implementation_created"] is False
    assert status["real_bridge_http_client_implemented"] is False
    assert status["network_transport_implemented"] is False
    assert status["network_transport_enabled"] is False
    assert status["network_transport_armed"] is False
    assert status["network_socket_opened"] is False
    assert status["bridge_post_call_implemented"] is False
    assert status["bridge_post_called"] is False
    assert status["routing_write_endpoint_implemented"] is False
    assert status["bridge_mutation_performed"] is False
    assert status["platform_db_mutation_performed"] is False
    assert status["lacrm_call_performed"] is False
    assert status["audit_row_created"] is False
    assert status["rollback_row_created"] is False
    assert status["rollback_snapshot_created"] is False
    assert status["cutover_packet_created"] is False
    assert status["live_write_enabled"] is False
    assert status["can_execute_bridge_write_now"] is False
    assert status["can_open_network_socket_now"] is False
    assert status["can_add_bridge_post_now"] is False

    stub = build_bridge_routing_network_transport_interface_stub()
    packet = build_sample_contract_packet()
    validation = stub.validate_contract_packet_shape(packet)
    assert validation["valid_contract_packet_shape"] is True
    assert validation["execution_implementation_created"] is False
    assert validation["network_transport_implemented"] is False
    assert validation["bridge_post_called"] is False

    with pytest.raises(BridgeRoutingNetworkTransportNotImplemented):
        stub.execute_bridge_routing_transport(packet.request)

    with pytest.raises(BridgeRoutingNetworkTransportNotImplemented):
        stub.open_network_boundary(packet.request)

    with pytest.raises(BridgeRoutingNetworkTransportNotImplemented):
        stub.call_bridge_post(packet.request)

    with pytest.raises(BridgeRoutingNetworkTransportNotImplemented):
        stub.create_audit_row(packet)

    with pytest.raises(BridgeRoutingNetworkTransportNotImplemented):
        stub.create_rollback_snapshot(packet)

    with pytest.raises(ValueError):
        BridgeRoutingNetworkTransportInterfaceStub(network_transport_implemented=True)

    packet_dict = bridge_routing_network_transport_interface_stub_packet_dict()
    assert packet_dict["status"]["interface_stub_scaffold_only"] is True
    assert packet_dict["sample_contract_validation"]["valid_contract_packet_shape"] is True


def test_interface_stub_source_has_no_transport_or_write_calls() -> None:
    service = read("app/services/routing_bridge_network_transport_interface_stub.py")
    assert "ROUTING_BRIDGE_NETWORK_TRANSPORT_INTERFACE_STUB_VERSION" in service
    assert "BridgeRoutingNetworkTransportInterfaceStub" in service
    assert "BridgeRoutingNetworkTransportNotImplemented" in service
    assert "execute_bridge_routing_transport" in service
    assert "open_network_boundary" in service
    assert "call_bridge_post" in service
    assert "create_audit_row" in service
    assert "create_rollback_snapshot" in service
    assert "Bridge routing network transport execution is not implemented in Phase 20 Step 35." in service
    assert "Opening a bridge routing network socket is not implemented in Phase 20 Step 35." in service
    assert "Calling bridge POST endpoints is not implemented in Phase 20 Step 35." in service
    assert '"execution_implementation_created": stub.execution_implementation_created' in service
    assert '"real_bridge_http_client_implemented": stub.real_bridge_http_client_implemented' in service
    assert '"network_transport_implemented": stub.network_transport_implemented' in service
    assert '"network_socket_opened": stub.network_socket_opened' in service
    assert '"bridge_post_call_implemented": stub.bridge_post_call_implemented' in service
    assert '"bridge_post_called": stub.bridge_post_called' in service
    assert '"routing_write_endpoint_implemented": stub.routing_write_endpoint_implemented' in service
    assert "import requests" not in service
    assert "requests." not in service
    assert "import httpx" not in service
    assert "httpx." not in service
    assert "import socket" not in service
    assert "socket." not in service
    assert ".commit(" not in service
    assert ".add(" not in service
    assert "Session(" not in service


def test_interface_stub_packet_script_is_get_only_and_no_write() -> None:
    script = read("scripts/phase20_generate_bridge_routing_network_transport_interface_stub_packet.ps1")
    assert "phase20_bridge_routing_network_transport_interface_stub_packet_" in script
    assert "bridge_routing_network_transport_interface_stub_packet_only = $true" in script
    assert "interface_stub_scaffold_only = $true" in script
    assert "non_network_interface_stub_created = $true" in script
    assert "execution_implementation_created = $false" in script
    assert "real_bridge_http_client_implemented = $false" in script
    assert "network_transport_implemented = $false" in script
    assert "network_transport_enabled = $false" in script
    assert "network_transport_armed = $false" in script
    assert "network_socket_opened = $false" in script
    assert "bridge_post_call_implemented = $false" in script
    assert "bridge_post_called = $false" in script
    assert "routing_write_endpoint_implemented = $false" in script
    assert "can_create_execution_implementation_now = $false" in script
    assert "execute_bridge_routing_transport" in script
    assert "open_network_boundary" in script
    assert "call_bridge_post" in script
    assert "phase20_bridge_routing_network_transport_contract_schema_packet_*" in script
    assert "routing_bridge_network_transport_interface_stub.py" in script
    assert "Invoke-RestMethod" in script
    assert "Invoke-RestMethod -Method Post" not in script
    assert "Set-Item" not in script
    assert "setx" not in script.lower()
    assert "Remove-Item" not in script
    assert "ConvertTo-Json -Depth 120" not in script


def test_interface_stub_packet_streamlit_page_is_report_only() -> None:
    page = read("ui/pages/87_Bridge_Routing_Network_Transport_Interface_Stub_Packet.py")
    assert "Phase 20 Bridge Routing Network Transport Interface Stub Packet" in page
    assert "network-transport-interface-stub-packet-only" in page
    assert "does not create execution implementation" in page
    assert "does not add a real bridge HTTP client" in page
    assert "does not add network transport" in page
    assert "does not enable network transport" in page
    assert "does not open network sockets" in page
    assert "does not call bridge POST endpoints" in page
    assert "does not create design-freeze records" in page
    assert "does not record operator signoffs" in page
    assert "does not create cutover packets" in page
    assert "does not capture bridge responses" in page
    assert "does not create response capture records" in page
    assert "does not set environment variables" in page
    assert "does not create audit rows" in page
    assert "does not write to the bridge" in page
    assert "does not call LACRM" in page
    assert "phase20_bridge_routing_network_transport_interface_stub_packet_*" in page
    assert "phase20_bridge_routing_network_transport_interface_stub_packet.json" in page
    assert "requests.get" not in page
    assert "requests.post" not in page
    assert "st.download_button" in page


def test_interface_stub_packet_docs_capture_boundaries() -> None:
    doc = read("docs/PHASE20_STEP35_BRIDGE_ROUTING_NETWORK_TRANSPORT_INTERFACE_STUB_PACKET.md")
    assert "non-network interface stub" in doc
    assert "network-transport-interface-stub-packet-only" in doc
    assert "NotImplementedError" in doc
    assert "does not create execution implementation" in doc
    assert "does not add a real bridge HTTP client" in doc
    assert "does not add network transport" in doc
    assert "does not open network sockets" in doc
    assert "does not call bridge POST endpoints" in doc
    assert "does not create design-freeze records" in doc
    assert "does not record operator signoffs" in doc
    assert "does not create cutover packets" in doc
    assert "does not capture bridge responses" in doc
    assert "does not create response capture records" in doc
    assert "does not set environment variables" in doc
    assert "does not create audit rows" in doc
    assert "does not mutate bridge state" in doc
    assert "does not call LACRM" in doc
    assert "Stage only the five Phase 20 Step 35 files" in doc
