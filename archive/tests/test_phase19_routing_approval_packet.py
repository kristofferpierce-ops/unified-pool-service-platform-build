from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def test_routing_approval_packet_generator_is_packet_only() -> None:
    script = read("scripts/phase19_generate_routing_approval_packet.ps1")
    assert "phase19_routing_approval_packet_" in script
    assert "packet_only = $true" in script
    assert "platform_db_mutation_performed = $false" in script
    assert "bridge_mutation_performed = $false" in script
    assert "bridge_post_called = $false" in script
    assert "lacrm_call_performed = $false" in script
    assert "routing_write_endpoint_implemented = $false" in script
    assert "operator_decision = \"unreviewed\"" in script
    assert "Export-Csv" in script
    assert "Invoke-RestMethod" not in script
    assert "Remove-Item" not in script


def test_routing_approval_packet_streamlit_page_warns_packet_only() -> None:
    page = read("ui/pages/26_Routing_Approval_Packet.py")
    assert "Phase 19 Routing Approval Packet" in page
    assert "packet-only" in page.lower()
    assert "does not save routing rules" in page
    assert "does not call bridge POST endpoints" in page
    assert "does not call LACRM" in page
    assert "phase19_routing_approval_packet_*" in page
    assert "requests.get" not in page
    assert "requests.post" not in page
    assert "st.download_button" in page


def test_routing_approval_packet_docs_capture_boundaries() -> None:
    doc = read("docs/PHASE19_STEP24_ROUTING_APPROVAL_PACKET.md")
    assert "operator review packet" in doc
    assert "does not save routing rules" in doc
    assert "does not mutate bridge state" in doc
    assert "does not call LACRM" in doc
    assert "Do not stage generated packets" in doc
