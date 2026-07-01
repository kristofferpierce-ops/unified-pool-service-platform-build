from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def test_routing_candidate_workbench_service_is_read_only() -> None:
    service = read("app/services/routing_candidate_workbench.py")
    assert "ROUTING_CANDIDATE_WORKBENCH_VERSION" in service
    assert "\"read_only\": True" in service
    assert "\"review_write_endpoint_implemented\": False" in service
    assert "\"candidate_review_write_enabled\": False" in service
    assert "\"bridge_post_enabled\": False" in service
    assert "\"lacrm_call_enabled\": False" in service
    assert "\"platform_db_mutation_performed\": False" in service
    assert ".commit(" not in service
    assert ".add(" not in service
    assert ".delete(" not in service


def test_routing_candidate_workbench_api_has_preview_only_post() -> None:
    route = read("app/api/routes/routing_candidate_workbench.py")
    assert "prefix=\"/front-desk/routing/candidate-workbench\"" in route
    assert "@router.get(\"/status\")" in route
    assert "@router.get(\"/queue\")" in route
    assert "@router.post(\"/{candidate_id}/review-preview\")" in route
    assert "preview_candidate_review" in route
    assert "@router.delete" not in route
    assert "@router.put" not in route
    assert "@router.patch" not in route


def test_routing_candidate_workbench_app_registration_is_present() -> None:
    app = read("app/api/app.py")
    assert "routing_candidate_workbench_router" in app
    assert "app.include_router(routing_candidate_workbench_router)" in app


def test_routing_candidate_workbench_script_checks_read_only_flags() -> None:
    script = read("scripts/phase19_check_routing_candidate_workbench.ps1")
    assert "phase19_routing_candidate_workbench_check_" in script
    assert "workbench_check_only = $true" in script
    assert "platform_db_mutation_performed = $false" in script
    assert "bridge_mutation_performed = $false" in script
    assert "bridge_post_called = $false" in script
    assert "lacrm_call_performed = $false" in script
    assert "/front-desk/routing/candidate-workbench/status" in script
    assert "Invoke-RestMethod" in script
    assert "Invoke-RestMethod -Method Post" not in script


def test_routing_candidate_workbench_streamlit_page_is_read_only() -> None:
    page = read("ui/pages/34_Routing_Candidate_Workbench.py")
    assert "Phase 19 Routing Candidate Workbench" in page
    assert "read-only" in page.lower()
    assert "does not save candidate decisions" in page
    assert "does not save routing rules" in page
    assert "does not call bridge POST endpoints" in page
    assert "does not call LACRM" in page
    assert "requests.get" in page
    assert "requests.post" not in page
    assert "st.download_button" in page


def test_routing_candidate_workbench_docs_capture_boundaries() -> None:
    doc = read("docs/PHASE19_STEP32_ROUTING_CANDIDATE_WORKBENCH.md")
    assert "read-only routing candidate workbench" in doc
    assert "does not implement candidate review writes yet" in doc
    assert "does not mutate bridge state" in doc
    assert "does not call LACRM" in doc
    assert "Do not stage generated workbench reports" in doc
