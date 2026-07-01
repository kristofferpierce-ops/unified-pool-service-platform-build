from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def test_bridge_routing_rollback_snapshot_script_is_get_only() -> None:
    script = read("scripts/phase19_capture_bridge_routing_rollback_snapshot.ps1")
    assert "phase19_bridge_routing_rollback_snapshot_" in script
    assert "bridge_routing_rollback_snapshot_only = $true" in script
    assert "bridge_get_only = $true" in script
    assert "platform_db_mutation_performed = $false" in script
    assert "bridge_mutation_performed = $false" in script
    assert "bridge_post_called = $false" in script
    assert "lacrm_call_performed = $false" in script
    assert "rollback_write_endpoint_implemented = $false" in script
    assert "routing_write_endpoint_implemented = $false" in script
    assert "/api/routing-rules" in script
    assert "/api/sms/batches?view=active" in script
    assert "rollback_payload_preview" in script
    assert "Invoke-RestMethod" in script
    assert "Invoke-RestMethod -Method Post" not in script
    assert "Remove-Item" not in script


def test_bridge_routing_rollback_snapshot_streamlit_page_is_report_only() -> None:
    page = read("ui/pages/43_Bridge_Routing_Rollback_Snapshot.py")
    assert "Phase 19 Bridge Routing Rollback Snapshot" in page
    assert "rollback-snapshot-only" in page.lower()
    assert "does not write to the bridge" in page
    assert "does not call bridge POST endpoints" in page
    assert "does not call LACRM" in page
    assert "phase19_bridge_routing_rollback_snapshot_*" in page
    assert "phase19_bridge_routing_rollback_snapshot.json" in page
    assert "requests.get" not in page
    assert "requests.post" not in page
    assert "st.download_button" in page


def test_bridge_routing_rollback_snapshot_docs_capture_boundaries() -> None:
    doc = read("docs/PHASE19_STEP41_BRIDGE_ROUTING_ROLLBACK_SNAPSHOT.md")
    assert "read-only bridge routing rollback snapshot" in doc
    assert "rollback-snapshot-only" in doc
    assert "bridge GET only" in doc
    assert "does not mutate bridge state" in doc
    assert "does not call LACRM" in doc
    assert "Do not stage generated rollback snapshot reports" in doc
