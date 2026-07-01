from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def test_bridge_routing_http_client_stub_service_has_no_real_http_client() -> None:
    service = read("app/services/routing_bridge_http_client_stub.py")
    assert "ROUTING_BRIDGE_HTTP_CLIENT_STUB_VERSION" in service
    assert "bridge_routing_http_client_stub_only" in service
    assert "\"real_bridge_http_client_implemented\": False" in service
    assert "\"bridge_http_client_implemented\": False" in service
    assert "\"bridge_post_call_implemented\": False" in service
    assert "\"bridge_post_called\": False" in service
    assert "\"bridge_mutation_performed\": False" in service
    assert "\"platform_db_mutation_performed\": False" in service
    assert "\"lacrm_call_performed\": False" in service
    assert "\"routing_write_endpoint_implemented\": False" in service
    assert "Real bridge HTTP client and bridge POST call are not implemented in Phase 20 Step 1." in service
    assert "request_template" in service
    assert "requests" not in service
    assert "httpx" not in service
    assert ".commit(" not in service
    assert ".add(" not in service
    assert ".delete(" not in service


def test_bridge_routing_http_client_stub_api_is_preview_only() -> None:
    route = read("app/api/routes/routing_bridge_http_client_stub.py")
    assert "prefix=\"/front-desk/routing/bridge-http-client-stub\"" in route
    assert "@router.get(\"/status\")" in route
    assert "@router.post(\"/preview\")" in route
    assert "build_bridge_routing_http_client_stub_preview" in route
    assert "@router.delete" not in route
    assert "@router.put" not in route
    assert "@router.patch" not in route


def test_bridge_routing_http_client_stub_app_registration_is_present() -> None:
    app = read("app/api/app.py")
    assert "routing_bridge_http_client_stub_router" in app
    assert "app.include_router(routing_bridge_http_client_stub_router)" in app


def test_bridge_routing_http_client_stub_script_posts_only_to_platform() -> None:
    script = read("scripts/phase20_generate_bridge_routing_http_client_stub.ps1")
    assert "phase20_bridge_routing_http_client_stub_" in script
    assert "bridge_routing_http_client_stub_only = $true" in script
    assert "platform_db_mutation_performed = $false" in script
    assert "bridge_mutation_performed = $false" in script
    assert "bridge_post_called = $false" in script
    assert "lacrm_call_performed = $false" in script
    assert "real_bridge_http_client_implemented = $false" in script
    assert "bridge_post_call_implemented = $false" in script
    assert "/front-desk/routing/bridge-http-client-stub/preview" in script
    assert "http://127.0.0.1:8000" not in script
    assert "$BridgeUrl" not in script
    assert "ConvertTo-Json -Depth 120" not in script


def test_bridge_routing_http_client_stub_streamlit_page_is_status_only() -> None:
    page = read("ui/pages/53_Bridge_Routing_HTTP_Client_Stub.py")
    assert "Phase 20 Bridge Routing HTTP Client Stub" in page
    assert "HTTP-client-stub-only" in page
    assert "does not write to the bridge" in page
    assert "does not call bridge POST endpoints" in page
    assert "does not call LACRM" in page
    assert "requests.get" in page
    assert "requests.post" not in page


def test_bridge_routing_http_client_stub_docs_capture_boundaries() -> None:
    doc = read("docs/PHASE20_STEP1_BRIDGE_ROUTING_HTTP_CLIENT_STUB.md")
    assert "stub-only HTTP client preview" in doc
    assert "HTTP-client-stub-only" in doc
    assert "does not mutate bridge state" in doc
    assert "does not call LACRM" in doc
    assert "add a real bridge HTTP client" in doc
    assert "Do not stage generated stub reports" in doc
