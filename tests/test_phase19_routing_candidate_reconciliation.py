from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def test_routing_candidate_reconciliation_script_is_read_only() -> None:
    script = read("scripts/phase19_reconcile_routing_candidates.ps1")
    assert "phase19_routing_candidate_reconciliation_" in script
    assert "reconciliation_only = $true" in script
    assert "platform_db_mutation_performed = $false" in script
    assert "bridge_mutation_performed = $false" in script
    assert "bridge_post_called = $false" in script
    assert "lacrm_call_performed = $false" in script
    assert "candidate_review_write_enabled = $false" in script
    assert "routing_write_endpoint_implemented = $false" in script
    assert "bridge_rule_missing_platform_candidate" in script
    assert "platform_candidate_missing_bridge_rule" in script
    assert "duplicate_platform_candidates_for_bridge_rule" in script
    assert "Invoke-RestMethod" in script
    assert "Invoke-RestMethod -Method Post" not in script
    assert "Remove-Item" not in script


def test_routing_candidate_reconciliation_streamlit_page_is_read_only() -> None:
    page = read("ui/pages/35_Routing_Candidate_Reconciliation.py")
    assert "Phase 19 Routing Candidate Reconciliation" in page
    assert "reconciliation-only" in page.lower()
    assert "does not save candidate decisions" in page
    assert "does not save routing rules" in page
    assert "does not call bridge POST endpoints" in page
    assert "does not call LACRM" in page
    assert "phase19_routing_candidate_reconciliation_*" in page
    assert "requests.get" not in page
    assert "requests.post" not in page
    assert "st.download_button" in page


def test_routing_candidate_reconciliation_docs_capture_boundaries() -> None:
    doc = read("docs/PHASE19_STEP33_ROUTING_CANDIDATE_RECONCILIATION.md")
    assert "latest bridge routing snapshot" in doc
    assert "platform `RoutingPreferenceCandidate` rows" in doc
    assert "reconciliation-only" in doc
    assert "does not mutate bridge state" in doc
    assert "does not call LACRM" in doc
    assert "Do not stage generated reconciliation reports" in doc
