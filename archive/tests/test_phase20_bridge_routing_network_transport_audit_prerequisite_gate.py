from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def test_bridge_routing_network_transport_audit_prerequisite_gate_script_is_get_only_and_no_write() -> None:
    script = read("scripts/phase20_generate_bridge_routing_network_transport_audit_prerequisite_gate.ps1")
    assert "phase20_bridge_routing_network_transport_audit_prerequisite_gate_" in script
    assert "bridge_routing_network_transport_audit_prerequisite_gate_only = $true" in script
    assert "bridge_get_only = $true" in script
    assert "audit_row_created = $false" in script
    assert "rollback_row_created = $false" in script
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
    assert "can_create_audit_rows_now = $false" in script
    assert "can_create_rollback_rows_now = $false" in script
    assert "transport_execution_id" in script
    assert "idempotency_key" in script
    assert "request_hash" in script
    assert "response_hash" in script
    assert "rollback_snapshot_id" in script
    assert "phase20_bridge_routing_network_transport_dry_run_invocation_path_release_checkpoint_*" in script
    assert "Invoke-RestMethod" in script
    assert "Invoke-RestMethod -Method Post" not in script
    assert "Remove-Item" not in script
    assert "ConvertTo-Json -Depth 120" not in script


def test_bridge_routing_network_transport_audit_prerequisite_gate_streamlit_page_is_report_only() -> None:
    page = read("ui/pages/76_Bridge_Routing_Network_Transport_Audit_Prerequisite_Gate.py")
    assert "Phase 20 Bridge Routing Network Transport Audit Prerequisite Gate" in page
    assert "network-transport-audit-prerequisite-gate-only" in page
    assert "does not create audit rows" in page
    assert "does not create rollback rows" in page
    assert "does not write to the bridge" in page
    assert "does not call bridge POST endpoints" in page
    assert "does not enable network transport" in page
    assert "does not open network sockets" in page
    assert "does not call LACRM" in page
    assert "phase20_bridge_routing_network_transport_audit_prerequisite_gate_*" in page
    assert "phase20_bridge_routing_network_transport_audit_prerequisite_gate.json" in page
    assert "requests.get" not in page
    assert "requests.post" not in page
    assert "st.download_button" in page


def test_bridge_routing_network_transport_audit_prerequisite_gate_docs_capture_boundaries() -> None:
    doc = read("docs/PHASE20_STEP24_BRIDGE_ROUTING_NETWORK_TRANSPORT_AUDIT_PREREQUISITE_GATE.md")
    assert "no-write audit prerequisite gate" in doc
    assert "network-transport-audit-prerequisite-gate-only" in doc
    assert "bridge GET only" in doc
    assert "does not create audit rows" in doc
    assert "does not create rollback rows" in doc
    assert "does not mutate bridge state" in doc
    assert "does not call LACRM" in doc
    assert "add a bridge POST implementation" in doc
    assert "Do not stage generated audit prerequisite reports" in doc
