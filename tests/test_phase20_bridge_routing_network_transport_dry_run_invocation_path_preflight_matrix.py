from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def test_bridge_routing_network_transport_dry_run_invocation_path_preflight_matrix_script_is_get_only() -> None:
    script = read("scripts/phase20_generate_bridge_routing_network_transport_dry_run_invocation_path_preflight_matrix.ps1")
    assert "phase20_bridge_routing_network_transport_dry_run_invocation_path_preflight_matrix_" in script
    assert "bridge_routing_network_transport_dry_run_invocation_path_preflight_matrix_only = $true" in script
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
    assert "phase20_bridge_routing_network_transport_dry_run_invocation_path_validation_*" in script
    assert "phase20_bridge_routing_network_transport_dry_run_invocation_path_*" in script
    assert "phase20_bridge_routing_network_transport_interface_scaffold_release_checkpoint_*" in script
    assert "phase20_bridge_routing_network_transport_interface_scaffold_operator_signoff_*" in script
    assert "BridgeRoutingNetworkTransportDryRunInvocationPath" in script
    assert "dry_run_invocation_path_only" in script
    assert "Invoke-RestMethod" in script
    assert "Invoke-RestMethod -Method Post" not in script
    assert "Remove-Item" not in script
    assert "ConvertTo-Json -Depth 120" not in script


def test_bridge_routing_network_transport_dry_run_invocation_path_preflight_matrix_streamlit_page_is_report_only() -> None:
    page = read("ui/pages/73_Bridge_Routing_Network_Transport_Dry_Run_Invocation_Path_Preflight_Matrix.py")
    assert "Phase 20 Bridge Routing Network Transport Dry Run Invocation Path Preflight Matrix" in page
    assert "network-transport-dry-run-invocation-path-preflight-matrix-only" in page
    assert "does not write to the bridge" in page
    assert "does not call bridge POST endpoints" in page
    assert "does not enable network transport" in page
    assert "does not open network sockets" in page
    assert "does not call LACRM" in page
    assert "phase20_bridge_routing_network_transport_dry_run_invocation_path_preflight_matrix_*" in page
    assert "phase20_bridge_routing_network_transport_dry_run_invocation_path_preflight_matrix.json" in page
    assert "requests.get" not in page
    assert "requests.post" not in page
    assert "st.download_button" in page


def test_bridge_routing_network_transport_dry_run_invocation_path_preflight_matrix_docs_capture_boundaries() -> None:
    doc = read("docs/PHASE20_STEP21_BRIDGE_ROUTING_NETWORK_TRANSPORT_DRY_RUN_INVOCATION_PATH_PREFLIGHT_MATRIX.md")
    assert "no-socket preflight matrix" in doc
    assert "network-transport-dry-run-invocation-path-preflight-matrix-only" in doc
    assert "bridge GET only" in doc
    assert "does not mutate bridge state" in doc
    assert "does not call LACRM" in doc
    assert "add a bridge POST implementation" in doc
    assert "Do not stage generated preflight matrix reports" in doc
