from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def test_bridge_routing_write_scaffold_service_has_no_bridge_client() -> None:
    service = read("app/services/routing_bridge_write_executor.py")
    assert "ROUTING_BRIDGE_WRITE_EXECUTOR_VERSION" in service
    assert "PLATFORM_BRIDGE_ROUTING_WRITE_ENABLED" in service
    assert "PLATFORM_BRIDGE_ROUTING_WRITE_ARMED" in service
    assert "WRITE BRIDGE ROUTING" in service
    assert "\"bridge_post_call_implemented\": False" in service
    assert "\"bridge_post_called\": False" in service
    assert "\"bridge_mutation_performed\": False" in service
    assert "\"platform_db_mutation_performed\": False" in service
    assert "\"lacrm_call_performed\": False" in service
    assert "\"routing_write_endpoint_implemented\": False" in service
    assert "Bridge POST call is not implemented in Step 45" in service
    assert "request_envelope_preview" in service
    assert "requests" not in service
    assert "httpx" not in service
    assert ".commit(" not in service
    assert ".add(" not in service
    assert ".delete(" not in service


def test_bridge_routing_write_scaffold_api_is_preview_only() -> None:
    route = read("app/api/routes/routing_bridge_write_executor.py")
    assert "prefix=\"/front-desk/routing/bridge-write-executor\"" in route
    assert "@router.get(\"/status\")" in route
    assert "@router.post(\"/preview\")" in route
    assert "execution_endpoint_available" in route
    assert "@router.delete" not in route
    assert "@router.put" not in route
    assert "@router.patch" not in route


def test_bridge_routing_write_scaffold_app_registration_is_present() -> None:
    app = read("app/api/app.py")
    assert "routing_bridge_write_executor_router" in app
    assert "app.include_router(routing_bridge_write_executor_router)" in app


def test_bridge_routing_write_scaffold_script_posts_only_to_platform() -> None:
    script = read("scripts/phase19_run_bridge_routing_write_scaffold.ps1")
    assert "phase19_bridge_routing_write_scaffold_" in script
    assert "bridge_routing_write_scaffold_only = $true" in script
    assert "platform_db_mutation_performed = $false" in script
    assert "bridge_mutation_performed = $false" in script
    assert "bridge_post_called = $false" in script
    assert "lacrm_call_performed = $false" in script
    assert "bridge_post_call_implemented = $false" in script
    assert "/front-desk/routing/bridge-write-executor/preview" in script
    assert "http://127.0.0.1:8000" not in script
    assert "$BridgeUrl" not in script


def test_bridge_routing_write_scaffold_streamlit_page_is_status_only() -> None:
    page = read("ui/pages/47_Bridge_Routing_Write_Scaffold.py")
    assert "Phase 19 Bridge Routing Write Scaffold" in page
    assert "does not trigger bridge writes" in page
    assert "does not write to the bridge" in page
    assert "does not call bridge POST endpoints" in page
    assert "does not call LACRM" in page
    assert "requests.get" in page
    assert "requests.post" not in page


def test_bridge_routing_write_scaffold_docs_capture_boundaries() -> None:
    doc = read("docs/PHASE19_STEP45_BRIDGE_ROUTING_WRITE_SCAFFOLD.md")
    assert "disabled-by-default bridge routing write scaffold preview" in doc
    assert "does not include a bridge HTTP client" in doc
    assert "scaffold-preview-only" in doc
    assert "does not mutate bridge state" in doc
    assert "does not call LACRM" in doc
    assert "Do not stage generated scaffold reports" in doc

def test_bridge_routing_write_scaffold_script_uses_valid_json_depth() -> None:
    script = read("scripts/phase19_run_bridge_routing_write_scaffold.ps1")
    assert "ConvertTo-Json -Depth 120" not in script
    assert "ConvertTo-Json -Depth 100" in script
