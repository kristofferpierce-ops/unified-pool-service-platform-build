from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def test_routing_bridge_apply_preview_service_is_preview_only() -> None:
    service = read("app/services/routing_bridge_apply_preview.py")
    assert "ROUTING_BRIDGE_APPLY_PREVIEW_VERSION" in service
    assert "\"read_only\": True" in service
    assert "\"preview_only\": True" in service
    assert "\"bridge_apply_enabled\": False" in service
    assert "\"bridge_apply_armed\": False" in service
    assert "\"bridge_post_called\": False" in service
    assert "\"bridge_write_endpoint_implemented\": False" in service
    assert "\"platform_db_mutation_performed\": False" in service
    assert "\"lacrm_call_performed\": False" in service
    assert "target_bridge_endpoint" in service
    assert ".commit(" not in service
    assert ".add(" not in service
    assert ".delete(" not in service


def test_routing_bridge_apply_preview_api_exposes_only_get_routes() -> None:
    route = read("app/api/routes/routing_bridge_apply_preview.py")
    assert "prefix=\"/front-desk/routing/bridge-apply-preview\"" in route
    assert "@router.get(\"/status\")" in route
    assert "@router.get(\"\")" in route
    assert "@router.post" not in route
    assert "@router.put" not in route
    assert "@router.patch" not in route
    assert "@router.delete" not in route


def test_routing_bridge_apply_preview_app_registration_is_present() -> None:
    app = read("app/api/app.py")
    assert "routing_bridge_apply_preview_router" in app
    assert "app.include_router(routing_bridge_apply_preview_router)" in app


def test_routing_bridge_apply_preview_script_checks_no_write_flags() -> None:
    script = read("scripts/phase19_generate_routing_bridge_apply_preview.ps1")
    assert "phase19_routing_bridge_apply_preview_" in script
    assert "bridge_apply_preview_only = $true" in script
    assert "platform_db_mutation_performed = $false" in script
    assert "bridge_mutation_performed = $false" in script
    assert "bridge_post_called = $false" in script
    assert "lacrm_call_performed = $false" in script
    assert "/front-desk/routing/bridge-apply-preview/status" in script
    assert "Invoke-RestMethod" in script
    assert "Invoke-RestMethod -Method Post" not in script


def test_routing_bridge_apply_preview_streamlit_page_is_preview_only() -> None:
    page = read("ui/pages/37_Routing_Bridge_Apply_Preview.py")
    assert "Phase 19 Routing Bridge Apply Preview" in page
    assert "preview-only" in page.lower()
    assert "does not write to the bridge" in page
    assert "does not call bridge POST endpoints" in page
    assert "does not call LACRM" in page
    assert "requests.get" in page
    assert "requests.post" not in page
    assert "st.download_button" in page


def test_routing_bridge_apply_preview_docs_capture_boundaries() -> None:
    doc = read("docs/PHASE19_STEP35_ROUTING_BRIDGE_APPLY_PREVIEW.md")
    assert "dry-run bridge apply preview" in doc
    assert "does not call the bridge" in doc
    assert "preview-only" in doc
    assert "does not mutate bridge state" in doc
    assert "does not call LACRM" in doc
    assert "Do not stage generated preview reports" in doc
