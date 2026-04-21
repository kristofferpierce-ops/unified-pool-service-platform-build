from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def test_routing_preference_draft_model_declares_schema_only_table() -> None:
    model = read("app/models/routing_preference_drafts.py")
    assert "class RoutingPreferenceDraft(SQLModel, table=True)" in model
    assert "__tablename__ = \"routing_preference_drafts\"" in model
    assert "draft_key" in model
    assert "candidate_id" in model
    assert "draft_schema_only_no_write" in model


def test_routing_preference_draft_service_is_read_only() -> None:
    service = read("app/services/routing_preference_drafts.py")
    assert "ROUTING_PREFERENCE_DRAFT_SCHEMA_VERSION" in service
    assert "\"read_only\": True" in service
    assert "\"draft_creation_enabled\": False" in service
    assert "\"draft_write_endpoint_implemented\": False" in service
    assert "\"bridge_post_enabled\": False" in service
    assert "\"lacrm_call_enabled\": False" in service
    assert "\"platform_db_mutation_performed\": False" in service
    assert "draft_preview_only_no_write" in service
    assert ".commit(" not in service
    assert ".add(" not in service
    assert ".delete(" not in service


def test_routing_preference_draft_api_exposes_read_and_preview_only_routes() -> None:
    route = read("app/api/routes/routing_preference_drafts.py")
    assert "prefix=\"/front-desk/routing/preference-drafts\"" in route
    assert "@router.get(\"/status\")" in route
    assert "@router.get(\"\")" in route
    assert "@router.get(\"/{draft_id}\")" in route
    assert "@router.post(\"/from-candidate-preview/{candidate_id}\")" in route
    assert "preview_draft_from_candidate" in route
    assert "@router.put" not in route
    assert "@router.patch" not in route
    assert "@router.delete" not in route


def test_routing_preference_draft_app_registration_is_present() -> None:
    app = read("app/api/app.py")
    assert "routing_preference_drafts_router" in app
    assert "app.include_router(routing_preference_drafts_router)" in app
    assert "app.models.routing_preference_drafts" in app


def test_routing_preference_draft_script_checks_read_only_flags() -> None:
    script = read("scripts/phase19_check_routing_preference_drafts.ps1")
    assert "phase19_routing_preference_draft_check_" in script
    assert "draft_check_only = $true" in script
    assert "platform_db_mutation_performed = $false" in script
    assert "bridge_mutation_performed = $false" in script
    assert "bridge_post_called = $false" in script
    assert "lacrm_call_performed = $false" in script
    assert "/front-desk/routing/preference-drafts/status" in script
    assert "Invoke-RestMethod" in script
    assert "Invoke-RestMethod -Method Post" not in script


def test_routing_preference_draft_streamlit_page_is_read_only() -> None:
    page = read("ui/pages/36_Routing_Preference_Drafts.py")
    assert "Phase 19 Routing Preference Drafts" in page
    assert "read-only" in page.lower()
    assert "does not create drafts" in page
    assert "does not save routing rules" in page
    assert "does not call bridge POST endpoints" in page
    assert "does not call LACRM" in page
    assert "requests.get" in page
    assert "requests.post" not in page
    assert "st.download_button" in page


def test_routing_preference_draft_docs_capture_boundaries() -> None:
    doc = read("docs/PHASE19_STEP34_ROUTING_PREFERENCE_DRAFTS.md")
    assert "schema/read-only only" in doc
    assert "does not create drafts yet" in doc
    assert "does not mutate bridge state" in doc
    assert "does not call LACRM" in doc
    assert "Do not stage generated draft reports" in doc
