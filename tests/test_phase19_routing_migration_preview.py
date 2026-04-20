from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def test_routing_migration_preview_generator_is_preview_only() -> None:
    script = read("scripts/phase19_generate_routing_migration_preview.ps1")
    assert "phase19_routing_migration_preview_" in script
    assert "preview_only = $true" in script
    assert "platform_db_mutation_performed = $false" in script
    assert "bridge_mutation_performed = $false" in script
    assert "bridge_post_called = $false" in script
    assert "lacrm_call_performed = $false" in script
    assert "RoutingPreference" in script
    assert "manual_review_required" in script
    assert "Invoke-RestMethod" not in script
    assert "Set-Content" in script
    assert "Remove-Item" not in script


def test_routing_migration_preview_streamlit_page_warns_preview_only() -> None:
    page = read("ui/pages/25_Routing_Migration_Preview.py")
    assert "Phase 19 Routing Migration Preview" in page
    assert "preview-only" in page.lower()
    assert "does not save routing rules" in page
    assert "does not call bridge POST endpoints" in page
    assert "does not call LACRM" in page
    assert "phase19_routing_migration_preview_*.json" in page
    assert "requests.get" not in page
    assert "requests.post" not in page
    assert "st.download_button" in page


def test_routing_migration_preview_docs_capture_boundaries() -> None:
    doc = read("docs/PHASE19_STEP23_ROUTING_MIGRATION_PREVIEW.md")
    assert "dry-run routing migration preview" in doc
    assert "does not save routing rules" in doc
    assert "does not mutate bridge state" in doc
    assert "does not call LACRM" in doc
    assert "Do not stage generated previews" in doc
