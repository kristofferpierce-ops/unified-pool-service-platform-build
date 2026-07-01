from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def test_bridge_routing_write_audit_writer_service_is_gated() -> None:
    service = read("app/services/routing_bridge_write_audit_writer.py")
    assert "ROUTING_BRIDGE_WRITE_AUDIT_WRITER_VERSION" in service
    assert "PLATFORM_BRIDGE_ROUTING_AUDIT_WRITE_ENABLED" in service
    assert "PLATFORM_BRIDGE_ROUTING_AUDIT_WRITE_ARMED" in service
    assert "CREATE BRIDGE ROUTING AUDIT ROWS" in service
    assert "\"audit_write_performed\": False" in service
    assert "\"platform_db_mutation_performed\": False" in service
    assert "\"bridge_mutation_performed\": False" in service
    assert "\"bridge_post_called\": False" in service
    assert "\"lacrm_call_performed\": False" in service
    assert "\"bridge_post_call_implemented\": False" in service
    assert "session.commit()" in service
    assert "requests" not in service
    assert "httpx" not in service


def test_bridge_routing_write_audit_writer_api_defaults_to_dry_run() -> None:
    route = read("app/api/routes/routing_bridge_write_audit_writer.py")
    assert "prefix=\"/front-desk/routing/bridge-write-audit-writer\"" in route
    assert "BridgeRoutingAuditWriteRequest" in route
    assert "dry_run: bool = True" in route
    assert "@router.get(\"/status\")" in route
    assert "@router.post(\"/run\")" in route
    assert "preview_bridge_routing_audit_write" in route
    assert "@router.delete" not in route
    assert "@router.put" not in route
    assert "@router.patch" not in route


def test_bridge_routing_write_audit_writer_app_registration_is_present() -> None:
    app = read("app/api/app.py")
    assert "routing_bridge_write_audit_writer_router" in app
    assert "app.include_router(routing_bridge_write_audit_writer_router)" in app


def test_bridge_routing_write_audit_writer_script_posts_only_to_platform() -> None:
    script = read("scripts/phase19_run_bridge_routing_write_audit_writer.ps1")
    assert "phase19_bridge_routing_write_audit_writer_run_" in script
    assert "dry_run = $dryRun" in script
    assert "/front-desk/routing/bridge-write-audit-writer/run" in script
    assert "bridge_post_called" in script
    assert "lacrm_call_performed" in script
    assert "http://127.0.0.1:8000" not in script
    assert "$BridgeUrl" not in script


def test_bridge_routing_write_audit_writer_streamlit_page_is_status_only() -> None:
    page = read("ui/pages/42_Bridge_Routing_Write_Audit_Writer.py")
    assert "Phase 19 Bridge Routing Write Audit Writer" in page
    assert "Disabled-by-default" in page
    assert "does not trigger audit writes" in page
    assert "does not write to the bridge" in page
    assert "does not call bridge POST endpoints" in page
    assert "does not call LACRM" in page
    assert "requests.get" in page
    assert "requests.post" not in page


def test_bridge_routing_write_audit_writer_docs_capture_boundaries() -> None:
    doc = read("docs/PHASE19_STEP40_BRIDGE_ROUTING_WRITE_AUDIT_WRITER.md")
    assert "Disabled-by-default" in doc
    assert "Dry-run mode performs no platform DB mutation" in doc
    assert "does not write to the bridge or LACRM" in doc
    assert "Do not stage generated audit writer runs" in doc
