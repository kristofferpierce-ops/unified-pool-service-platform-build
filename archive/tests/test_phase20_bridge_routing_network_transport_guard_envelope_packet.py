from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def test_guard_envelope_module_is_preview_only_and_importable() -> None:
    from app.services.routing_bridge_network_transport_contract_schema import build_sample_contract_packet
    from app.services.routing_bridge_network_transport_guard_envelope import (
        BridgeRoutingNetworkTransportGuardBlocked,
        BridgeRoutingNetworkTransportGuardEnvelope,
        bridge_routing_network_transport_guard_envelope_packet_dict,
        bridge_routing_network_transport_guard_envelope_status,
        build_bridge_routing_network_transport_guard_envelope,
    )

    status = bridge_routing_network_transport_guard_envelope_status()
    assert status["guard_envelope_only"] is True
    assert status["dry_run_adapter_wrapper_required"] is True
    assert status["preview_only_guard_created"] is True
    assert status["execution_implementation_created"] is False
    assert status["real_bridge_http_client_implemented"] is False
    assert status["network_transport_implemented"] is False
    assert status["network_transport_enabled"] is False
    assert status["network_transport_armed"] is False
    assert status["network_socket_opened"] is False
    assert status["bridge_post_call_implemented"] is False
    assert status["bridge_post_called"] is False
    assert status["routing_write_endpoint_implemented"] is False
    assert status["bridge_response_captured"] is False
    assert status["response_capture_record_created"] is False
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

    guard = build_bridge_routing_network_transport_guard_envelope()
    packet = build_sample_contract_packet()
    decision = guard.evaluate_preview(packet)
    assert decision.guard_envelope_only is True
    assert decision.guard_preview_created is True
    assert decision.guard_decision == "preview_allowed_no_execution"
    assert decision.future_execution_allowed is False
    assert decision.execution_implementation_created is False
    assert decision.network_transport_implemented is False
    assert decision.network_socket_opened is False
    assert decision.bridge_post_called is False
    assert decision.bridge_response_captured is False

    with pytest.raises(BridgeRoutingNetworkTransportGuardBlocked):
        guard.block_future_execution_attempt()

    with pytest.raises(ValueError):
        BridgeRoutingNetworkTransportGuardEnvelope(network_transport_implemented=True)

    packet_dict = bridge_routing_network_transport_guard_envelope_packet_dict()
    assert packet_dict["status"]["guard_envelope_only"] is True
    assert packet_dict["sample_guard_decision"]["guard_preview_created"] is True


def test_guard_envelope_source_has_no_transport_or_write_calls() -> None:
    service = read("app/services/routing_bridge_network_transport_guard_envelope.py")
    assert "ROUTING_BRIDGE_NETWORK_TRANSPORT_GUARD_ENVELOPE_VERSION" in service
    assert "BridgeRoutingNetworkTransportGuardEnvelope" in service
    assert "BridgeRoutingNetworkTransportGuardEnvelopeDecisionResult" in service
    assert "BridgeRoutingNetworkTransportGuardBlocked" in service
    assert "evaluate_preview" in service
    assert "_validate_preview_safety" in service
    assert "block_future_execution_attempt" in service
    assert "guard_envelope_only" in service
    assert "guard_preview_created" in service
    assert '"execution_implementation_created": guard.execution_implementation_created' in service
    assert '"real_bridge_http_client_implemented": guard.real_bridge_http_client_implemented' in service
    assert '"network_transport_implemented": guard.network_transport_implemented' in service
    assert '"network_socket_opened": guard.network_socket_opened' in service
    assert '"bridge_post_call_implemented": guard.bridge_post_call_implemented' in service
    assert '"bridge_post_called": guard.bridge_post_called' in service
    assert '"routing_write_endpoint_implemented": guard.routing_write_endpoint_implemented' in service
    assert ".execute_bridge_routing_transport(" not in service
    assert ".open_network_boundary(" not in service
    assert ".call_bridge_post(" not in service
    assert "import requests" not in service
    assert "requests." not in service
    assert "import httpx" not in service
    assert "httpx." not in service
    assert "import socket" not in service
    assert "socket." not in service
    assert ".commit(" not in service
    assert ".add(" not in service
    assert "Session(" not in service


def test_guard_envelope_packet_script_is_get_only_and_no_write() -> None:
    script = read("scripts/phase20_generate_bridge_routing_network_transport_guard_envelope_packet.ps1")
    assert "phase20_bridge_routing_network_transport_guard_envelope_packet_" in script
    assert "bridge_routing_network_transport_guard_envelope_packet_only = $true" in script
    assert "guard_envelope_only = $true" in script
    assert "guard_preview_created = $true" in script
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
    assert "evaluate_preview" in script
    assert "block_future_execution_attempt" in script
    assert "phase20_bridge_routing_network_transport_dry_run_adapter_wrapper_packet_*" in script
    assert "routing_bridge_network_transport_guard_envelope.py" in script
    assert "Invoke-RestMethod" in script
    assert "Invoke-RestMethod -Method Post" not in script
    assert "Set-Item" not in script
    assert "setx" not in script.lower()
    assert "Remove-Item" not in script
    assert "ConvertTo-Json -Depth 120" not in script


def test_guard_envelope_packet_streamlit_page_is_report_only() -> None:
    page = read("ui/pages/89_Bridge_Routing_Network_Transport_Guard_Envelope_Packet.py")
    assert "Phase 20 Bridge Routing Network Transport Guard Envelope Packet" in page
    assert "network-transport-guard-envelope-packet-only" in page
    assert "does not create execution implementation" in page
    assert "does not call interface execution methods" in page
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
    assert "phase20_bridge_routing_network_transport_guard_envelope_packet_*" in page
    assert "phase20_bridge_routing_network_transport_guard_envelope_packet.json" in page
    assert "requests.get" not in page
    assert "requests.post" not in page
    assert "st.download_button" in page


def test_guard_envelope_packet_docs_capture_boundaries() -> None:
    doc = read("docs/PHASE20_STEP37_BRIDGE_ROUTING_NETWORK_TRANSPORT_GUARD_ENVELOPE_PACKET.md")
    assert "preview-only guard envelope" in doc
    assert "network-transport-guard-envelope-packet-only" in doc
    assert "does not create execution implementation" in doc
    assert "does not call interface execution methods" in doc
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
    assert "Stage only the five Phase 20 Step 37 files" in doc
