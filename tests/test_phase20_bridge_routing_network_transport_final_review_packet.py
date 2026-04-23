from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def test_final_review_packet_module_is_no_write_and_importable() -> None:
    from app.services.routing_bridge_network_transport_contract_schema import build_sample_contract_packet
    from app.services.routing_bridge_network_transport_final_review_packet import (
        BridgeRoutingNetworkTransportFinalReviewPacket,
        BridgeRoutingNetworkTransportFinalReviewPacketResult,
        bridge_routing_network_transport_final_review_packet_dict,
        bridge_routing_network_transport_final_review_packet_status,
        build_bridge_routing_network_transport_final_review_packet,
    )

    status = bridge_routing_network_transport_final_review_packet_status()
    assert status["final_review_packet_only"] is True
    assert status["readiness_report_required"] is True
    assert status["preview_only_final_review_created"] is True
    assert status["final_approval_recorded"] is False
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
    assert status["can_record_final_approval_now"] is False

    review = build_bridge_routing_network_transport_final_review_packet()
    packet = build_sample_contract_packet()
    final_review = review.build_final_review(packet)
    assert final_review.final_review_packet_only is True
    assert final_review.final_review_preview_created is True
    assert final_review.final_review_status == "final_review_ready_no_execution"
    assert final_review.final_approval_recorded is False
    assert final_review.future_execution_allowed is False
    assert final_review.execution_implementation_created is False
    assert final_review.network_transport_implemented is False
    assert final_review.network_socket_opened is False
    assert final_review.bridge_post_called is False
    assert final_review.bridge_response_captured is False

    with pytest.raises(ValueError):
        BridgeRoutingNetworkTransportFinalReviewPacket(network_transport_implemented=True)

    with pytest.raises(ValueError):
        BridgeRoutingNetworkTransportFinalReviewPacketResult(
            final_review_packet_id="bad",
            transport_execution_id="bad",
            request_id="bad",
            bridge_post_called=True,
        )

    packet_dict = bridge_routing_network_transport_final_review_packet_dict()
    assert packet_dict["status"]["final_review_packet_only"] is True
    assert packet_dict["sample_final_review_packet"]["final_review_preview_created"] is True


def test_final_review_packet_source_has_no_transport_or_write_calls() -> None:
    service = read("app/services/routing_bridge_network_transport_final_review_packet.py")
    assert "ROUTING_BRIDGE_NETWORK_TRANSPORT_FINAL_REVIEW_PACKET_VERSION" in service
    assert "BridgeRoutingNetworkTransportFinalReviewPacket" in service
    assert "BridgeRoutingNetworkTransportFinalReviewPacketResult" in service
    assert "build_final_review" in service
    assert "_validate_readiness_report" in service
    assert "final_review_packet_only" in service
    assert "final_review_preview_created" in service
    assert '"final_approval_recorded": packet.final_approval_recorded' in service
    assert '"execution_implementation_created": packet.execution_implementation_created' in service
    assert '"real_bridge_http_client_implemented": packet.real_bridge_http_client_implemented' in service
    assert '"network_transport_implemented": packet.network_transport_implemented' in service
    assert '"network_socket_opened": packet.network_socket_opened' in service
    assert '"bridge_post_call_implemented": packet.bridge_post_call_implemented' in service
    assert '"bridge_post_called": packet.bridge_post_called' in service
    assert '"routing_write_endpoint_implemented": packet.routing_write_endpoint_implemented' in service
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


def test_final_review_packet_script_is_get_only_and_no_write() -> None:
    script = read("scripts/phase20_generate_bridge_routing_network_transport_final_review_packet.ps1")
    assert "phase20_bridge_routing_network_transport_final_review_packet_" in script
    assert "bridge_routing_network_transport_final_review_packet_only = $true" in script
    assert "final_review_packet_only = $true" in script
    assert "final_review_preview_created = $true" in script
    assert "final_approval_recorded = $false" in script
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
    assert "can_record_final_approval_now = $false" in script
    assert "build_final_review" in script
    assert "phase20_bridge_routing_network_transport_readiness_report_packet_*" in script
    assert "routing_bridge_network_transport_final_review_packet.py" in script
    assert "Invoke-RestMethod" in script
    assert "Invoke-RestMethod -Method Post" not in script
    assert "Set-Item" not in script
    assert "setx" not in script.lower()
    assert "Remove-Item" not in script
    assert "ConvertTo-Json -Depth 120" not in script


def test_final_review_packet_streamlit_page_is_report_only() -> None:
    page = read("ui/pages/91_Bridge_Routing_Network_Transport_Final_Review_Packet.py")
    assert "Phase 20 Bridge Routing Network Transport Final Review Packet" in page
    assert "network-transport-final-review-packet-only" in page
    assert "does not record final approvals" in page
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
    assert "phase20_bridge_routing_network_transport_final_review_packet_*" in page
    assert "phase20_bridge_routing_network_transport_final_review_packet.json" in page
    assert "requests.get" not in page
    assert "requests.post" not in page
    assert "st.download_button" in page


def test_final_review_packet_docs_capture_boundaries() -> None:
    doc = read("docs/PHASE20_STEP39_BRIDGE_ROUTING_NETWORK_TRANSPORT_FINAL_REVIEW_PACKET.md")
    assert "no-write final review packet" in doc
    assert "network-transport-final-review-packet-only" in doc
    assert "does not record final approvals" in doc
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
    assert "Stage only the five Phase 20 Step 39 files" in doc
