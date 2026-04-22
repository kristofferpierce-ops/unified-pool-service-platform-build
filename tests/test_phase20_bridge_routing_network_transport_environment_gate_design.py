from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def test_bridge_routing_network_transport_environment_gate_design_script_is_get_only_and_no_write() -> None:
    script = read("scripts/phase20_generate_bridge_routing_network_transport_environment_gate_design.ps1")
    assert "phase20_bridge_routing_network_transport_environment_gate_design_" in script
    assert "bridge_routing_network_transport_environment_gate_design_only = $true" in script
    assert "bridge_get_only = $true" in script
    assert "environment_variables_set = $false" in script
    assert "rollback_snapshot_created = $false" in script
    assert "rollback_row_created = $false" in script
    assert "audit_row_created = $false" in script
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
    assert "can_set_environment_variables_now = $false" in script
    assert "PLATFORM_BRIDGE_NETWORK_TRANSPORT_MODE" in script
    assert "PLATFORM_BRIDGE_NETWORK_TRANSPORT_DESIGN_ENABLED" in script
    assert "PLATFORM_BRIDGE_NETWORK_TRANSPORT_DESIGN_ARMED" in script
    assert "PLATFORM_BRIDGE_ROUTING_WRITE_ENABLED" in script
    assert "PLATFORM_BRIDGE_ROUTING_WRITE_ARMED" in script
    assert "PLATFORM_BRIDGE_BASE_URL" in script
    assert "PLATFORM_BRIDGE_ADMIN_TOKEN" in script
    assert "phase20_bridge_routing_network_transport_rollback_snapshot_prerequisite_gate_*" in script
    assert "Invoke-RestMethod" in script
    assert "Invoke-RestMethod -Method Post" not in script
    assert "Set-Item" not in script
    assert "setx" not in script.lower()
    assert "Remove-Item" not in script
    assert "ConvertTo-Json -Depth 120" not in script


def test_bridge_routing_network_transport_environment_gate_design_streamlit_page_is_report_only() -> None:
    page = read("ui/pages/78_Bridge_Routing_Network_Transport_Environment_Gate_Design.py")
    assert "Phase 20 Bridge Routing Network Transport Environment Gate Design" in page
    assert "network-transport-environment-gate-design-only" in page
    assert "does not set environment variables" in page
    assert "does not create rollback snapshots" in page
    assert "does not create audit rows" in page
    assert "does not write to the bridge" in page
    assert "does not call bridge POST endpoints" in page
    assert "does not enable network transport" in page
    assert "does not open network sockets" in page
    assert "does not call LACRM" in page
    assert "phase20_bridge_routing_network_transport_environment_gate_design_*" in page
    assert "phase20_bridge_routing_network_transport_environment_gate_design.json" in page
    assert "requests.get" not in page
    assert "requests.post" not in page
    assert "st.download_button" in page


def test_bridge_routing_network_transport_environment_gate_design_docs_capture_boundaries() -> None:
    doc = read("docs/PHASE20_STEP26_BRIDGE_ROUTING_NETWORK_TRANSPORT_ENVIRONMENT_GATE_DESIGN.md")
    assert "no-write environment gate design" in doc
    assert "network-transport-environment-gate-design-only" in doc
    assert "bridge GET only" in doc
    assert "does not set environment variables" in doc
    assert "does not create rollback snapshots" in doc
    assert "does not create rollback rows" in doc
    assert "does not create audit rows" in doc
    assert "does not mutate bridge state" in doc
    assert "does not call LACRM" in doc
    assert "add a bridge POST implementation" in doc
    assert "Do not stage generated environment gate reports" in doc
