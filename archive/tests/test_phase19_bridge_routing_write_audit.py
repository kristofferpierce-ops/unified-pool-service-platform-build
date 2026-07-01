from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def test_bridge_routing_write_audit_model_declares_schema_only_table() -> None:
    model = read("app/models/routing_bridge_write_audit.py")
    assert "class RoutingBridgeWriteAudit(SQLModel, table=True)" in model
    assert "__tablename__ = \"routing_bridge_write_audits\"" in model
    assert "audit_key" in model
    assert "previous_bridge_rule_json" in model
    assert "rollback_payload_json" in model
    assert "bridge_post_called" in model
    assert "bridge_mutation_performed" in model


def test_bridge_routing_write_audit_service_is_read_only() -> None:
    service = read("app/services/routing_bridge_write_audit.py")
    assert "ROUTING_BRIDGE_WRITE_AUDIT_SCHEMA_VERSION" in service
    assert "\"read_only\": True" in service
    assert "\"audit_write_enabled\": False" in service
    assert "\"audit_write_endpoint_implemented\": False" in service
    assert "\"rollback_write_endpoint_implemented\": False" in service
    assert "\"bridge_post_enabled\": False" in service
    assert "\"bridge_write_endpoint_implemented\": False" in service
    assert "\"lacrm_call_enabled\": False" in service
    assert "\"platform_db_mutation_performed\": False" in service
    assert "not_available_until_previous_bridge_rule_is_captured" in service
    assert ".commit(" not in service
    assert ".add(" not in service
    assert ".delete(" not in service


def test_bridge_routing_write_audit_api_has_read_and_preview_only_routes() -> None:
    route = read("app/api/routes/routing_bridge_write_audit.py")
    assert "prefix=\"/front-desk/routing/bridge-write-audit\"" in route
    assert "@router.get(\"/status\")" in route
    assert "@router.get(\"\")" in route
    assert "@router.get(\"/{audit_id}\")" in route
    assert "@router.post(\"/preview-from-rehearsal\")" in route
    assert "preview_audit_from_rehearsal" in route
    assert "@router.put" not in route
    assert "@router.patch" not in route
    assert "@router.delete" not in route


def test_bridge_routing_write_audit_app_registration_is_present() -> None:
    app = read("app/api/app.py")
    assert "routing_bridge_write_audit_router" in app
    assert "app.include_router(routing_bridge_write_audit_router)" in app
    assert "app.models.routing_bridge_write_audit" in app


def test_bridge_routing_write_audit_script_checks_no_write_flags() -> None:
    script = read("scripts/phase19_check_bridge_routing_write_audit.ps1")
    assert "phase19_bridge_routing_write_audit_check_" in script
    assert "bridge_routing_write_audit_check_only = $true" in script
    assert "platform_db_mutation_performed = $false" in script
    assert "bridge_mutation_performed = $false" in script
    assert "bridge_post_called = $false" in script
    assert "lacrm_call_performed = $false" in script
    assert "audit_write_endpoint_implemented = $false" in script
    assert "rollback_write_endpoint_implemented = $false" in script
    assert "/front-desk/routing/bridge-write-audit/status" in script
    assert "Invoke-RestMethod" in script
    assert "Invoke-RestMethod -Method Post" not in script


def test_bridge_routing_write_audit_streamlit_page_is_read_only() -> None:
    page = read("ui/pages/40_Bridge_Routing_Write_Audit.py")
    assert "Phase 19 Bridge Routing Write Audit" in page
    assert "read-only" in page.lower()
    assert "does not create audit rows" in page
    assert "does not write to the bridge" in page
    assert "does not call bridge POST endpoints" in page
    assert "does not call LACRM" in page
    assert "requests.get" in page
    assert "requests.post" not in page
    assert "st.download_button" in page


def test_bridge_routing_write_audit_docs_capture_boundaries() -> None:
    doc = read("docs/PHASE19_STEP38_BRIDGE_ROUTING_WRITE_AUDIT.md")
    assert "audit and rollback ledger foundation" in doc
    assert "schema/read-only only" in doc
    assert "does not create audit rows yet" in doc
    assert "does not mutate bridge state" in doc
    assert "does not call LACRM" in doc
    assert "Do not stage generated audit check reports" in doc
