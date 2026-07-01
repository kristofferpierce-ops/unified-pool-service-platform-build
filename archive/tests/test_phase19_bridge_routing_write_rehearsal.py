from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def test_bridge_routing_write_rehearsal_service_is_blocked_by_default() -> None:
    service = read("app/services/routing_bridge_write_rehearsal.py")
    assert "ROUTING_BRIDGE_WRITE_REHEARSAL_VERSION" in service
    assert "PLATFORM_BRIDGE_ROUTING_WRITE_ENABLED" in service
    assert "PLATFORM_BRIDGE_ROUTING_WRITE_ARMED" in service
    assert "WRITE BRIDGE ROUTING" in service
    assert "\"rehearsal_only\": True" in service
    assert "\"bridge_post_call_implemented\": False" in service
    assert "\"bridge_post_called\": False" in service
    assert "\"platform_db_mutation_performed\": False" in service
    assert "\"bridge_mutation_performed\": False" in service
    assert "\"lacrm_call_performed\": False" in service
    assert "Bridge POST call is not implemented in Step 37" in service
    assert "requests" not in service
    assert "httpx" not in service
    assert ".commit(" not in service
    assert ".add(" not in service
    assert ".delete(" not in service


def test_bridge_routing_write_rehearsal_api_has_local_post_only() -> None:
    route = read("app/api/routes/routing_bridge_write_rehearsal.py")
    assert "prefix=\"/front-desk/routing/bridge-write-rehearsal\"" in route
    assert "@router.get(\"/status\")" in route
    assert "@router.post(\"/rehearse\")" in route
    assert "rehearse_bridge_routing_write" in route
    assert "@router.delete" not in route
    assert "@router.put" not in route
    assert "@router.patch" not in route


def test_bridge_routing_write_rehearsal_app_registration_is_present() -> None:
    app = read("app/api/app.py")
    assert "routing_bridge_write_rehearsal_router" in app
    assert "app.include_router(routing_bridge_write_rehearsal_router)" in app


def test_bridge_routing_write_rehearsal_script_does_not_call_bridge() -> None:
    script = read("scripts/phase19_run_bridge_routing_write_rehearsal.ps1")
    assert "phase19_bridge_routing_write_rehearsal_" in script
    assert "bridge_routing_write_rehearsal_only = $true" in script
    assert "platform_db_mutation_performed = $false" in script
    assert "bridge_mutation_performed = $false" in script
    assert "bridge_post_called = $false" in script
    assert "lacrm_call_performed = $false" in script
    assert "/front-desk/routing/bridge-write-rehearsal/status" in script
    assert "/front-desk/routing/bridge-write-rehearsal/rehearse" in script
    assert "http://127.0.0.1:8000" not in script
    assert "$BridgeUrl" not in script


def test_bridge_routing_write_rehearsal_streamlit_page_is_status_only() -> None:
    page = read("ui/pages/39_Bridge_Routing_Write_Rehearsal.py")
    assert "Phase 19 Bridge Routing Write Rehearsal" in page
    assert "does not trigger rehearsals" in page
    assert "does not write to the bridge" in page
    assert "does not call bridge POST endpoints" in page
    assert "does not call LACRM" in page
    assert "requests.get" in page
    assert "requests.post" not in page
    assert "st.download_button" in page


def test_bridge_routing_write_rehearsal_docs_capture_boundaries() -> None:
    doc = read("docs/PHASE19_STEP37_BRIDGE_ROUTING_WRITE_REHEARSAL.md")
    assert "blocked by default" in doc
    assert "does not implement or perform the outbound bridge POST call" in doc
    assert "rehearsal-only" in doc
    assert "does not mutate bridge state" in doc
    assert "does not call LACRM" in doc
    assert "Do not stage generated rehearsal reports" in doc
