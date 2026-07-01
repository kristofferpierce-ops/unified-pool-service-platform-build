from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def test_bridge_routing_write_audit_plan_script_is_plan_only() -> None:
    script = read("scripts/phase19_plan_bridge_routing_write_audit.ps1")
    assert "phase19_bridge_routing_write_audit_plan_" in script
    assert "bridge_routing_write_audit_plan_only = $true" in script
    assert "platform_db_mutation_performed = $false" in script
    assert "bridge_mutation_performed = $false" in script
    assert "bridge_post_called = $false" in script
    assert "lacrm_call_performed = $false" in script
    assert "audit_write_endpoint_implemented = $false" in script
    assert "rollback_write_endpoint_implemented = $false" in script
    assert "would_create_audit_row" in script
    assert "would_skip_existing_audit_row" in script
    assert "/front-desk/routing/bridge-write-audit/preview-from-rehearsal" in script
    assert "Invoke-RestMethod" in script
    assert "http://127.0.0.1:8000" not in script
    assert "$BridgeUrl" not in script
    assert "Remove-Item" not in script


def test_bridge_routing_write_audit_plan_streamlit_page_is_report_only() -> None:
    page = read("ui/pages/41_Bridge_Routing_Write_Audit_Plan.py")
    assert "Phase 19 Bridge Routing Write Audit Plan" in page
    assert "audit-plan-only" in page.lower()
    assert "does not create audit rows" in page
    assert "does not write to the bridge" in page
    assert "does not call bridge POST endpoints" in page
    assert "does not call LACRM" in page
    assert "phase19_bridge_routing_write_audit_plan_*" in page
    assert "phase19_bridge_routing_write_audit_plan.json" in page
    assert "requests.get" not in page
    assert "requests.post" not in page
    assert "st.download_button" in page


def test_bridge_routing_write_audit_plan_docs_capture_boundaries() -> None:
    doc = read("docs/PHASE19_STEP39_BRIDGE_ROUTING_WRITE_AUDIT_PLAN.md")
    assert "dry-run audit-row plan" in doc
    assert "does not create audit rows" in doc
    assert "audit-plan-only" in doc
    assert "does not mutate bridge state" in doc
    assert "does not call LACRM" in doc
    assert "Do not stage generated audit plan reports" in doc
