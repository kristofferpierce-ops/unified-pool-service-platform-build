from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def test_routing_candidate_model_declares_schema_only_table() -> None:
    model = read("app/models/routing_candidates.py")
    assert "class RoutingPreferenceCandidate(SQLModel, table=True)" in model
    assert "__tablename__ = \"routing_preference_candidates\"" in model
    assert "preference_key" in model
    assert "eligible_for_future_dry_run_import" in model
    assert "schema_only_no_import" in model
    assert "bridge" not in model.lower() or "does not" in model.lower()


def test_routing_candidate_service_is_read_only() -> None:
    service = read("app/services/routing_candidates.py")
    assert "ROUTING_CANDIDATE_SCHEMA_VERSION" in service
    assert "candidate_import_enabled" in service
    assert "\"routing_write_endpoint_implemented\": False" in service
    assert "\"bridge_post_enabled\": False" in service
    assert "\"lacrm_call_enabled\": False" in service
    assert ".add(" not in service
    assert ".delete(" not in service
    assert ".commit(" not in service


def test_routing_candidate_api_exposes_only_get_routes() -> None:
    route = read("app/api/routes/routing_candidates.py")
    assert "prefix=\"/front-desk/routing\"" in route
    assert "@router.get(\"/candidates/status\")" in route
    assert "@router.get(\"/candidates\")" in route
    assert "@router.get(\"/candidates/{candidate_id}\")" in route
    assert "@router.post" not in route
    assert "@router.put" not in route
    assert "@router.patch" not in route
    assert "@router.delete" not in route


def test_routing_candidate_app_registration_is_present() -> None:
    app = read("app/api/app.py")
    assert "routing_candidates_router" in app
    assert "app.include_router(routing_candidates_router)" in app
    assert "app.models.routing_candidates" in app


def test_routing_candidate_streamlit_page_is_read_only() -> None:
    page = read("ui/pages/31_Routing_Candidates.py")
    assert "Phase 19 Routing Candidates" in page
    assert "read-only" in page.lower()
    assert "does not import candidates" in page
    assert "does not save routing rules" in page
    assert "does not call bridge POST endpoints" in page
    assert "does not call LACRM" in page
    assert "/front-desk/routing/candidates/status" in page
    assert "requests.get" in page
    assert "requests.post" not in page


def test_routing_candidate_docs_capture_boundaries() -> None:
    doc = read("docs/PHASE19_STEP29_ROUTING_CANDIDATE_SCHEMA.md")
    assert "schema/read-only only" in doc
    assert "does not import rows yet" in doc
    assert "does not call LACRM" in doc
    assert "does not mutate bridge state" in doc
    assert "Do not stage generated backups" in doc
