from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def test_routing_import_plan_generator_is_import_plan_only() -> None:
    script = read("scripts/phase19_generate_routing_import_plan.ps1")
    assert "phase19_routing_import_plan_" in script
    assert "import_plan_only = $true" in script
    assert "platform_db_mutation_performed = $false" in script
    assert "bridge_mutation_performed = $false" in script
    assert "bridge_post_called = $false" in script
    assert "lacrm_call_performed = $false" in script
    assert "routing_write_endpoint_implemented = $false" in script
    assert "RoutingPreferenceCandidate" in script
    assert "eligible_for_future_dry_run_import" in script
    assert "Import-Csv" in script
    assert "Invoke-RestMethod" not in script
    assert "Remove-Item" not in script


def test_routing_import_plan_streamlit_page_is_read_only() -> None:
    page = read("ui/pages/29_Routing_Import_Plan.py")
    assert "Phase 19 Routing Import Plan" in page
    assert "import-plan-only" in page.lower()
    assert "does not save routing rules" in page
    assert "does not call bridge POST endpoints" in page
    assert "does not call LACRM" in page
    assert "phase19_routing_import_plan_*" in page
    assert "requests.get" not in page
    assert "requests.post" not in page
    assert "st.download_button" in page


def test_routing_import_plan_docs_capture_boundaries() -> None:
    doc = read("docs/PHASE19_STEP27_ROUTING_IMPORT_PLAN.md")
    assert "dry-run import plan" in doc
    assert "import-plan-only" in doc
    assert "does not save routing rules" in doc
    assert "does not mutate bridge state" in doc
    assert "does not call LACRM" in doc
    assert "Do not stage generated import plans" in doc
