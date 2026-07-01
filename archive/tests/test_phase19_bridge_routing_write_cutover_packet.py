from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def test_bridge_routing_write_cutover_packet_script_is_packet_only() -> None:
    script = read("scripts/phase19_generate_bridge_routing_write_cutover_packet.ps1")
    assert "phase19_bridge_routing_write_cutover_packet_" in script
    assert "bridge_routing_write_cutover_packet_only = $true" in script
    assert "platform_db_mutation_performed = $false" in script
    assert "bridge_mutation_performed = $false" in script
    assert "bridge_post_called = $false" in script
    assert "lacrm_call_performed = $false" in script
    assert "live_write_enabled = $false" in script
    assert "routing_write_endpoint_implemented = $false" in script
    assert "bridge_write_implementation_added = $false" in script
    assert "can_execute_bridge_write_now = $false" in script
    assert "phase19_bridge_routing_write_readiness_*" in script
    assert "phase19_bridge_routing_write_contract_*" in script
    assert "phase19_routing_bridge_apply_preview_*" in script
    assert "phase19_bridge_routing_write_rehearsal_*" in script
    assert "phase19_bridge_routing_write_audit_plan_*" in script
    assert "phase19_bridge_routing_write_audit_writer_run_*" in script
    assert "phase19_bridge_routing_rollback_snapshot_*" in script
    assert "Invoke-RestMethod" in script
    assert "Invoke-RestMethod -Method Post" not in script
    assert "Remove-Item" not in script


def test_bridge_routing_write_cutover_packet_streamlit_page_is_report_only() -> None:
    page = read("ui/pages/45_Bridge_Routing_Write_Cutover_Packet.py")
    assert "Phase 19 Bridge Routing Write Cutover Packet" in page
    assert "cutover-packet-only" in page.lower()
    assert "does not write to the bridge" in page
    assert "does not call bridge POST endpoints" in page
    assert "does not call LACRM" in page
    assert "phase19_bridge_routing_write_cutover_packet_*" in page
    assert "phase19_bridge_routing_write_cutover_packet.json" in page
    assert "requests.get" not in page
    assert "requests.post" not in page
    assert "st.download_button" in page


def test_bridge_routing_write_cutover_packet_docs_capture_boundaries() -> None:
    doc = read("docs/PHASE19_STEP43_BRIDGE_ROUTING_WRITE_CUTOVER_PACKET.md")
    assert "operator-review cutover packet" in doc
    assert "cutover-packet-only" in doc
    assert "does not mutate bridge state" in doc
    assert "does not call LACRM" in doc
    assert "add a bridge write implementation" in doc
    assert "Do not stage generated cutover packets" in doc

def test_bridge_routing_write_cutover_packet_script_uses_ascii_checklist_text() -> None:
    script = read("scripts/phase19_generate_bridge_routing_write_cutover_packet.ps1")
    assert "\u00e2\u20ac\u201d" not in script
    assert "\u2014" not in script
    assert '"- [{0}] {1}: {2} - {3}" -f' in script
