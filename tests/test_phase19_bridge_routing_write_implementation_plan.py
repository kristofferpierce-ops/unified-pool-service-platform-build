from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def test_bridge_routing_write_implementation_plan_script_is_plan_only() -> None:
    script = read("scripts/phase19_generate_bridge_routing_write_implementation_plan.ps1")
    assert "phase19_bridge_routing_write_implementation_plan_" in script
    assert "bridge_routing_write_implementation_plan_only = $true" in script
    assert "platform_db_mutation_performed = $false" in script
    assert "bridge_mutation_performed = $false" in script
    assert "bridge_post_called = $false" in script
    assert "lacrm_call_performed = $false" in script
    assert "live_write_enabled = $false" in script
    assert "routing_write_endpoint_implemented = $false" in script
    assert "bridge_write_implementation_added = $false" in script
    assert "can_execute_bridge_write_now = $false" in script
    assert "phase19_bridge_routing_write_cutover_packet_*" in script
    assert "routing_bridge_write_client.py" in script
    assert "routing_bridge_write_executor.py" in script
    assert "PLATFORM_BRIDGE_ROUTING_WRITE_ENABLED" in script
    assert "WRITE BRIDGE ROUTING" in script
    assert "Invoke-RestMethod" in script
    assert "Invoke-RestMethod -Method Post" not in script
    assert "Remove-Item" not in script


def test_bridge_routing_write_implementation_plan_streamlit_page_is_report_only() -> None:
    page = read("ui/pages/46_Bridge_Routing_Write_Implementation_Plan.py")
    assert "Phase 19 Bridge Routing Write Implementation Plan" in page
    assert "implementation-plan-only" in page.lower()
    assert "does not write to the bridge" in page
    assert "does not call bridge POST endpoints" in page
    assert "does not add bridge write implementation" in page
    assert "does not call LACRM" in page
    assert "phase19_bridge_routing_write_implementation_plan_*" in page
    assert "phase19_bridge_routing_write_implementation_plan.json" in page
    assert "requests.get" not in page
    assert "requests.post" not in page
    assert "st.download_button" in page


def test_bridge_routing_write_implementation_plan_docs_capture_boundaries() -> None:
    doc = read("docs/PHASE19_STEP44_BRIDGE_ROUTING_WRITE_IMPLEMENTATION_PLAN.md")
    assert "design plan for a future guarded bridge routing write scaffold" in doc
    assert "implementation-plan-only" in doc
    assert "does not mutate bridge state" in doc
    assert "does not call LACRM" in doc
    assert "add a bridge write implementation" in doc
    assert "Do not stage generated implementation plans" in doc
