from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def test_routing_candidate_import_service_is_gated() -> None:
    service = read("app/services/routing_candidate_import.py")
    assert "PLATFORM_ROUTING_CANDIDATE_IMPORT_ENABLED" in service
    assert "PLATFORM_ROUTING_CANDIDATE_IMPORT_ARMED" in service
    assert "IMPORT ROUTING CANDIDATES" in service
    assert "candidate_import_performed\": False" in service
    assert "platform_db_mutation_performed\": False" in service
    assert "bridge_mutation_performed\": False" in service
    assert "bridge_post_called\": False" in service
    assert "lacrm_call_performed\": False" in service
    assert "session.commit()" in service


def test_routing_candidate_import_api_defaults_to_dry_run() -> None:
    route = read("app/api/routes/routing_candidate_import.py")
    assert "RoutingCandidateImportRequest" in route
    assert "dry_run: bool = True" in route
    assert "@router.get(\"/candidates/import/status\")" in route
    assert "@router.post(\"/candidates/import-plan\")" in route
    assert "preview_routing_candidate_import" in route
    assert "@router.delete" not in route


def test_routing_candidate_import_app_registration_is_present() -> None:
    app = read("app/api/app.py")
    assert "routing_candidate_import_router" in app
    assert "app.include_router(routing_candidate_import_router)" in app


def test_routing_candidate_import_script_uses_post_but_no_bridge_or_lacrm() -> None:
    script = read("scripts/phase19_run_routing_candidate_import.ps1")
    assert "phase19_routing_candidate_import_run_" in script
    assert "dry_run = $dryRun" in script
    assert "/front-desk/routing/candidates/import-plan" in script
    assert "Invoke-RestMethod" in script
    assert "bridge_post_called" in script
    assert "lacrm_call_performed" in script


def test_routing_candidate_import_streamlit_page_is_status_only() -> None:
    page = read("ui/pages/33_Routing_Candidate_Import.py")
    assert "Phase 19 Routing Candidate Import" in page
    assert "Disabled-by-default" in page
    assert "does not trigger imports" in page
    assert "/front-desk/routing/candidates/import/status" in page
    assert "requests.get" in page
    assert "requests.post" not in page


def test_routing_candidate_import_docs_capture_boundaries() -> None:
    doc = read("docs/PHASE19_STEP31_ROUTING_CANDIDATE_IMPORT.md")
    assert "disabled-by-default" in doc
    assert "Dry-run mode performs no platform DB mutation" in doc
    assert "does not write to the bridge or LACRM" in doc
    assert "Do not stage generated import runs" in doc
