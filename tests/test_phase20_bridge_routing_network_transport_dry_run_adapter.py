from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def test_bridge_routing_network_transport_dry_run_adapter_service_has_no_real_transport() -> None:
    service = read("app/services/routing_bridge_network_transport_dry_run_adapter.py")
    assert "ROUTING_BRIDGE_NETWORK_TRANSPORT_DRY_RUN_ADAPTER_VERSION" in service
    assert "bridge_routing_network_transport_dry_run_adapter_only" in service
    assert "\"real_bridge_http_client_implemented\": False" in service
    assert "\"network_transport_implemented\": False" in service
    assert "\"network_transport_enabled\": False" in service
    assert "\"network_transport_armed\": False" in service
    assert "\"network_socket_opened\": False" in service
    assert "\"bridge_post_call_implemented\": False" in service
    assert "\"bridge_post_called\": False" in service
    assert "\"bridge_mutation_performed\": False" in service
    assert "\"platform_db_mutation_performed\": False" in service
    assert "\"lacrm_call_performed\": False" in service
    assert "\"routing_write_endpoint_implemented\": False" in service
    assert "Real bridge network transport and bridge POST call are not implemented in Phase 20 Step 8." in service
    assert "dry_run_adapter_harness" in service
    assert "requests" not in service
    assert "httpx" not in service
    assert ".commit(" not in service
    assert ".add(" not in service
    assert ".delete(" not in service


def test_bridge_routing_network_transport_dry_run_adapter_api_is_simulation_only() -> None:
    route = read("app/api/routes/routing_bridge_network_transport_dry_run_adapter.py")
    assert "prefix=\"/front-desk/routing/bridge-network-transport-dry-run-adapter\"" in route
    assert "@router.get(\"/status\")" in route
    assert "@router.post(\"/simulate\")" in route
    assert "build_bridge_routing_network_transport_dry_run_adapter" in route
    assert "@router.delete" not in route
    assert "@router.put" not in route
    assert "@router.patch" not in route


def test_bridge_routing_network_transport_dry_run_adapter_app_registration_is_present() -> None:
    app = read("app/api/app.py")
    assert "routing_bridge_network_transport_dry_run_adapter_router" in app
    assert "app.include_router(routing_bridge_network_transport_dry_run_adapter_router)" in app


def test_bridge_routing_network_transport_dry_run_adapter_script_posts_only_to_platform() -> None:
    script = read("scripts/phase20_generate_bridge_routing_network_transport_dry_run_adapter.ps1")
    assert "phase20_bridge_routing_network_transport_dry_run_adapter_" in script
    assert "bridge_routing_network_transport_dry_run_adapter_only = $true" in script
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
    assert "/front-desk/routing/bridge-network-transport-dry-run-adapter/simulate" in script
    assert "http://127.0.0.1:8000" not in script
    assert "$BridgeUrl" not in script
    assert "ConvertTo-Json -Depth 120" not in script


def test_bridge_routing_network_transport_dry_run_adapter_streamlit_page_is_status_only() -> None:
    page = read("ui/pages/60_Bridge_Routing_Network_Transport_Dry_Run_Adapter.py")
    assert "Phase 20 Bridge Routing Network Transport Dry Run Adapter" in page
    assert "network-transport-dry-run-adapter-only" in page
    assert "does not write to the bridge" in page
    assert "does not call bridge POST endpoints" in page
    assert "does not call LACRM" in page
    assert "requests.get" in page
    assert "requests.post" not in page


def test_bridge_routing_network_transport_dry_run_adapter_docs_capture_boundaries() -> None:
    doc = read("docs/PHASE20_STEP8_BRIDGE_ROUTING_NETWORK_TRANSPORT_DRY_RUN_ADAPTER.md")
    assert "dry-run adapter harness" in doc
    assert "network-transport-dry-run-adapter-only" in doc
    assert "does not mutate bridge state" in doc
    assert "does not call LACRM" in doc
    assert "open network sockets" in doc
    assert "Do not stage generated dry-run adapter reports" in doc
