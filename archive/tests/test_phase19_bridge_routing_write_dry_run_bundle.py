from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def test_bridge_routing_write_dry_run_bundle_service_has_no_bridge_client() -> None:
    service = read("app/services/routing_bridge_write_dry_run_bundle.py")
    assert "ROUTING_BRIDGE_WRITE_DRY_RUN_BUNDLE_VERSION" in service
    assert "dry_run_bundle_only" in service
    assert "\"bridge_http_client_implemented\": False" in service
    assert "\"bridge_post_call_implemented\": False" in service
    assert "\"bridge_post_called\": False" in service
    assert "\"bridge_mutation_performed\": False" in service
    assert "\"platform_db_mutation_performed\": False" in service
    assert "\"lacrm_call_performed\": False" in service
    assert "\"routing_write_endpoint_implemented\": False" in service
    assert "Bridge HTTP client and bridge POST call are not implemented in Step 46." in service
    assert "request_template_only" in service
    assert "requests" not in service
    assert "httpx" not in service
    assert ".commit(" not in service
    assert ".add(" not in service
    assert ".delete(" not in service


def test_bridge_routing_write_dry_run_bundle_api_is_preview_only() -> None:
    route = read("app/api/routes/routing_bridge_write_dry_run_bundle.py")
    assert "prefix=\"/front-desk/routing/bridge-write-dry-run-bundle\"" in route
    assert "@router.get(\"/status\")" in route
    assert "@router.post(\"/build-preview\")" in route
    assert "build_bridge_routing_write_dry_run_bundle" in route
    assert "@router.delete" not in route
    assert "@router.put" not in route
    assert "@router.patch" not in route


def test_bridge_routing_write_dry_run_bundle_app_registration_is_present() -> None:
    app = read("app/api/app.py")
    assert "routing_bridge_write_dry_run_bundle_router" in app
    assert "app.include_router(routing_bridge_write_dry_run_bundle_router)" in app


def test_bridge_routing_write_dry_run_bundle_script_posts_only_to_platform() -> None:
    script = read("scripts/phase19_generate_bridge_routing_write_dry_run_bundle.ps1")
    assert "phase19_bridge_routing_write_dry_run_bundle_" in script
    assert "bridge_routing_write_dry_run_bundle_only = $true" in script
    assert "platform_db_mutation_performed = $false" in script
    assert "bridge_mutation_performed = $false" in script
    assert "bridge_post_called = $false" in script
    assert "lacrm_call_performed = $false" in script
    assert "bridge_http_client_implemented = $false" in script
    assert "bridge_post_call_implemented = $false" in script
    assert "/front-desk/routing/bridge-write-dry-run-bundle/build-preview" in script
    assert "http://127.0.0.1:8000" not in script
    assert "$BridgeUrl" not in script
    assert "ConvertTo-Json -Depth 120" not in script


def test_bridge_routing_write_dry_run_bundle_streamlit_page_is_status_only() -> None:
    page = read("ui/pages/48_Bridge_Routing_Write_Dry_Run_Bundle.py")
    assert "Phase 19 Bridge Routing Write Dry-run Bundle" in page
    assert "does not trigger bridge writes" in page
    assert "does not write to the bridge" in page
    assert "does not call bridge POST endpoints" in page
    assert "does not call LACRM" in page
    assert "requests.get" in page
    assert "requests.post" not in page


def test_bridge_routing_write_dry_run_bundle_docs_capture_boundaries() -> None:
    doc = read("docs/PHASE19_STEP46_BRIDGE_ROUTING_WRITE_DRY_RUN_BUNDLE.md")
    assert "dry-run request bundle" in doc
    assert "does not include a bridge HTTP client" in doc
    assert "dry-run-bundle-only" in doc
    assert "does not mutate bridge state" in doc
    assert "does not call LACRM" in doc
    assert "Do not stage generated dry-run bundle reports" in doc
