from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def test_readiness_report_module_is_no_write_and_importable() -> None:
    from app.services.routing_bridge_network_transport_contract_schema import build_sample_contract_packet
    from app.services.routing_bridge_network_transport_readiness_report import (
        BridgeRoutingNetworkTransportReadinessReport,
        BridgeRoutingNetworkTransportReadinessReportResult,
        bridge_routing_network_transport_readiness_report_packet_dict,
        bridge_routing_network_transport_readiness_report_status,
        build_bridge_routing_network_transport_readiness_report,
    )

    status = bridge_routing_network_transport_readiness_report_status()
    assert status["readiness_report_only"] is True
    assert status["guard_envelope_required"] is True
    assert status["preview_only_report_created"] is True
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

    report = build_bridge_routing_network_transport_readiness_report()
    packet = build_sample_contract_packet()
    readiness = report.build_report(packet)
    assert readiness.readiness_report_only is True
    assert readiness.readiness_preview_created is True
    assert readiness.readiness_status == "ready_for_review_no_execution"
    assert readiness.future_execution_allowed is False
    assert readiness.execution_implementation_created is False
    assert readiness.network_transport_implemented is False
    assert readiness.network_socket_opened is False
    assert readiness.bridge_post_called is False
    assert readiness.bridge_response_captured is False

    with pytest.raises(ValueError):
        BridgeRoutingNetworkTransportReadinessReport(network_transport_implemented=True)

    with pytest.raises(ValueError):
        BridgeRoutingNetworkTransportReadinessReportResult(
            readiness_report_id="bad",
            transport_execution_id="bad",
            request_id="bad",
            bridge_post_called=True,
        )

    packet_dict = bridge_routing_network_transport_readiness_report_packet_dict()
    assert packet_dict["status"]["readiness_report_only"] is True
    assert packet_dict["sample_readiness_report"]["readiness_preview_created"] is True


def test_readiness_report_source_has_no_transport_or_write_calls() -> None:
    service = read("app/services/routing_bridge_network_transport_readiness_report.py")
    assert "ROUTING_BRIDGE_NETWORK_TRANSPORT_READINESS_REPORT_VERSION" in service
    assert "BridgeRoutingNetworkTransportReadinessReport" in service
    assert "BridgeRoutingNetworkTransportReadinessReportResult" in service
    assert "build_report" in service
    assert "_validate_guard_decision" in service
    assert "readiness_report_only" in service
    assert "readiness_preview_created" in service
    assert '"execution_implementation_created": report.execution_implementation_created' in service
    assert '"real_bridge_http_client_implemented": report.real_bridge_http_client_implemented' in service
    assert '"network_transport_implemented": report.network_transport_implemented' in service
    assert '"network_socket_opened": report.network_socket_opened' in service
    assert '"bridge_post_call_implemented": report.bridge_post_call_implemented' in service
    assert '"bridge_post_called": report.bridge_post_called' in service
    assert '"routing_write_endpoint_implemented": report.routing_write_endpoint_implemented' in service
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


def test_readiness_report_packet_script_is_get_only_and_no_write() -> None:
    script = read("scripts/phase20_generate_bridge_routing_network_transport_readiness_report_packet.ps1")
    assert "phase20_bridge_routing_network_transport_readiness_report_packet_" in script
    assert "bridge_routing_network_transport_readiness_report_packet_only = $true" in script
    assert "readiness_report_only = $true" in script
    assert "readiness_preview_created = $true" in script
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
    assert "build_report" in script
    assert "phase20_bridge_routing_network_transport_guard_envelope_packet_*" in script
    assert "routing_bridge_network_transport_readiness_report.py" in script
    assert "Invoke-RestMethod" in script
    assert "Invoke-RestMethod -Method Post" not in script
    assert "Set-Item" not in script
    assert "setx" not in script.lower()
    assert "Remove-Item" not in script
    assert "ConvertTo-Json -Depth 120" not in script


def test_readiness_report_packet_streamlit_page_is_report_only() -> None:
    page = read("ui/pages/90_Bridge_Routing_Network_Transport_Readiness_Report_Packet.py")
    assert "Phase 20 Bridge Routing Network Transport Readiness Report Packet" in page
    assert "network-transport-readiness-report-packet-only" in page
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
    assert "phase20_bridge_routing_network_transport_readiness_report_packet_*" in page
    assert "phase20_bridge_routing_network_transport_readiness_report_packet.json" in page
    assert "requests.get" not in page
    assert "requests.post" not in page
    assert "st.download_button" in page


def test_readiness_report_packet_docs_capture_boundaries() -> None:
    doc = read("docs/PHASE20_STEP38_BRIDGE_ROUTING_NETWORK_TRANSPORT_READINESS_REPORT_PACKET.md")
    assert "no-write readiness report" in doc
    assert "network-transport-readiness-report-packet-only" in doc
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
    assert "Stage only the five Phase 20 Step 38 files" in doc
