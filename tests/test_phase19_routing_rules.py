from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def test_routing_snapshot_generator_is_read_only() -> None:
    script = read("scripts/phase19_generate_routing_rules_snapshot.ps1")
    assert "phase19_routing_rules_snapshot_" in script
    assert "routingRuleSummary" in script
    assert "setManualBtn" in script
    assert "/api/sms/batches?view=active" in script
    assert "/api/sms/batches?view=processed" in script
    assert "/api/routing-rules" in script
    assert "bridge_routing_mutation_performed = $false" in script
    assert "bridge_routing_post_called = $false" in script
    assert "Invoke-RestMethod" in script
    assert "Invoke-RestMethod -Method Post" not in script
    assert "Remove-Item" not in script


def test_routing_streamlit_page_warns_read_only() -> None:
    page = read("ui/pages/24_Routing_Rules.py")
    assert "Phase 19 Routing Rules" in page
    assert "read-only" in page.lower()
    assert "does not save routing rules" in page
    assert "does not call bridge POST endpoints" in page
    assert "does not call LACRM" in page
    assert "/api/sms/batches?view=active" in page
    assert "/api/sms/batches?view=processed" in page
    assert "/api/routing-rules" in page
    assert "requests.get" in page
    assert "requests.post" not in page


def test_routing_docs_capture_bridge_boundaries() -> None:
    doc = read("docs/PHASE19_STEP22_ROUTING_RULES.md")
    assert "bridge routing rules" in doc
    assert "does not call LACRM" in doc
    assert "does not mutate bridge state" in doc
    assert "does not save routing rules" in doc
    assert "original KPS Bridge / Data Hub UI" in doc
