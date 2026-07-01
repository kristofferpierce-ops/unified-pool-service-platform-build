from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def test_contract_schema_module_is_schema_only_and_importable() -> None:
    from app.services.routing_bridge_network_transport_contract_schema import (
        BridgeRoutingTransportRequestContract,
        BridgeRoutingTransportResponseContract,
        bridge_routing_network_transport_contract_schema_dict,
        bridge_routing_network_transport_contract_schema_status,
        build_sample_contract_packet,
    )

    status = bridge_routing_network_transport_contract_schema_status()
    assert status["contract_schema_scaffold_only"] is True
    assert status["schema_only_code_created"] is True
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
    assert status["can_open_network_boundary_now"] is False
    assert status["can_call_bridge_post_now"] is False

    packet = build_sample_contract_packet()
    assert packet.contract_schema_scaffold_only is True
    assert packet.can_execute_bridge_write_now is False
    assert packet.can_open_network_boundary_now is False
    assert packet.can_call_bridge_post_now is False

    schema_dict = bridge_routing_network_transport_contract_schema_dict()
    assert "request_fields" in schema_dict["schema"]
    assert "response_fields" in schema_dict["schema"]
    assert "audit_fields" in schema_dict["schema"]
    assert "rollback_fields" in schema_dict["schema"]
    assert "cutover_fields" in schema_dict["schema"]

    with pytest.raises(ValueError):
        BridgeRoutingTransportRequestContract(
            request_id="bad",
            transport_execution_id="bad",
            idempotency_key="bad",
            phone="+10000000000",
            mode="manual",
            owner_type="unknown",
            dry_run=False,
        )

    with pytest.raises(ValueError):
        BridgeRoutingTransportResponseContract(
            response_capture_id="bad",
            transport_execution_id="bad",
            bridge_post_called=True,
        )


def test_contract_schema_source_has_no_transport_or_write_calls() -> None:
    service = read("app/services/routing_bridge_network_transport_contract_schema.py")
    assert "ROUTING_BRIDGE_NETWORK_TRANSPORT_CONTRACT_SCHEMA_VERSION" in service
    assert "BridgeRoutingTransportRequestContract" in service
    assert "BridgeRoutingTransportResponseContract" in service
    assert "BridgeRoutingAuditContract" in service
    assert "BridgeRoutingRollbackContract" in service
    assert "BridgeRoutingCutoverContract" in service
    assert "BridgeRoutingNetworkTransportContractPacket" in service
    assert "contract_schema_scaffold_only" in service
    assert '"execution_implementation_created": False' in service
    assert '"real_bridge_http_client_implemented": False' in service
    assert '"network_transport_implemented": False' in service
    assert '"network_socket_opened": False' in service
    assert '"bridge_post_call_implemented": False' in service
    assert '"bridge_post_called": False' in service
    assert '"routing_write_endpoint_implemented": False' in service
    assert "import requests" not in service
    assert "requests." not in service
    assert "import httpx" not in service
    assert "httpx." not in service
    assert "import socket" not in service
    assert "socket." not in service
    assert ".commit(" not in service
    assert ".add(" not in service
    assert "Session(" not in service


def test_contract_schema_packet_script_is_get_only_and_no_write() -> None:
    script = read("scripts/phase20_generate_bridge_routing_network_transport_contract_schema_packet.ps1")
    assert "phase20_bridge_routing_network_transport_contract_schema_packet_" in script
    assert "bridge_routing_network_transport_contract_schema_packet_only = $true" in script
    assert "contract_schema_scaffold_only = $true" in script
    assert "schema_only_code_created = $true" in script
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
    assert "phase20_bridge_routing_network_transport_implementation_boundary_packet_*" in script
    assert "routing_bridge_network_transport_contract_schema.py" in script
    assert "Invoke-RestMethod" in script
    assert "Invoke-RestMethod -Method Post" not in script
    assert "Set-Item" not in script
    assert "setx" not in script.lower()
    assert "Remove-Item" not in script
    assert "ConvertTo-Json -Depth 120" not in script


def test_contract_schema_packet_streamlit_page_is_report_only() -> None:
    page = read("ui/pages/86_Bridge_Routing_Network_Transport_Contract_Schema_Packet.py")
    assert "Phase 20 Bridge Routing Network Transport Contract Schema Packet" in page
    assert "network-transport-contract-schema-packet-only" in page
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
    assert "phase20_bridge_routing_network_transport_contract_schema_packet_*" in page
    assert "phase20_bridge_routing_network_transport_contract_schema_packet.json" in page
    assert "requests.get" not in page
    assert "requests.post" not in page
    assert "st.download_button" in page


def test_contract_schema_packet_docs_capture_boundaries() -> None:
    doc = read("docs/PHASE20_STEP34_BRIDGE_ROUTING_NETWORK_TRANSPORT_CONTRACT_SCHEMA_PACKET.md")
    assert "schema-only post-boundary contract scaffold" in doc
    assert "network-transport-contract-schema-packet-only" in doc
    assert "schema-only" in doc
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
    assert "Stage only the five Phase 20 Step 34 files" in doc
