from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def test_phase20_network_transport_evidence_index_script_is_get_only_and_no_write() -> None:
    script = read("scripts/phase21_generate_phase20_network_transport_evidence_index.ps1")
    assert "phase21_phase20_network_transport_evidence_index_" in script
    assert "phase20_network_transport_evidence_index_only = $true" in script
    assert "evidence_index_only = $true" in script
    assert "bridge_get_only = $true" in script
    assert "design_closure_record_created = $false" in script
    assert "final_approval_recorded = $false" in script
    assert "implementation_phase_started = $false" in script
    assert "execution_implementation_created = $false" in script
    assert "real_bridge_http_client_implemented = $false" in script
    assert "network_transport_implemented = $false" in script
    assert "network_transport_enabled = $false" in script
    assert "network_transport_armed = $false" in script
    assert "network_socket_opened = $false" in script
    assert "bridge_post_call_implemented = $false" in script
    assert "bridge_post_called = $false" in script
    assert "routing_write_endpoint_implemented = $false" in script
    assert "can_create_execution_implementation_now = $false" in script
    assert "can_record_final_approval_now = $false" in script
    assert "can_start_implementation_phase_now = $false" in script
    assert "phase20_bridge_routing_network_transport_design_closure_packet_*" in script
    assert "phase20_bridge_routing_network_transport_final_review_packet_*" in script
    assert "phase20_bridge_routing_network_transport_readiness_report_packet_*" in script
    assert "Invoke-RestMethod" in script
    assert "Invoke-RestMethod -Method Post" not in script
    assert "Set-Item" not in script
    assert "setx" not in script.lower()
    assert "Remove-Item" not in script
    assert "ConvertTo-Json -Depth 120" not in script


def test_phase20_network_transport_evidence_index_streamlit_page_is_report_only() -> None:
    page = read("ui/pages/93_Phase20_Network_Transport_Evidence_Index.py")
    assert "Phase 21 Step 1 - Phase 20 Network Transport Evidence Index" in page
    assert "Phase 20 network transport evidence-index-only" in page
    assert "does not create design closure records" in page
    assert "does not record final approvals" in page
    assert "does not start an implementation phase" in page
    assert "does not create execution implementation" in page
    assert "does not call interface execution methods" in page
    assert "does not add a real bridge HTTP client" in page
    assert "does not add network transport" in page
    assert "does not enable network transport" in page
    assert "does not open network sockets" in page
    assert "does not call bridge POST endpoints" in page
    assert "does not create design-freeze records" in page
    assert "does not record operator signoffs" in page
    assert "does not create cutover packets" in page
    assert "does not capture bridge responses" in page
    assert "does not create response capture records" in page
    assert "does not set environment variables" in page
    assert "does not create audit rows" in page
    assert "does not write to the bridge" in page
    assert "does not call LACRM" in page
    assert "phase21_phase20_network_transport_evidence_index_*" in page
    assert "phase21_phase20_network_transport_evidence_index.json" in page
    assert "requests.get" not in page
    assert "requests.post" not in page
    assert "st.download_button" in page


def test_phase20_network_transport_evidence_index_docs_capture_boundaries() -> None:
    doc = read("docs/PHASE21_STEP1_PHASE20_NETWORK_TRANSPORT_EVIDENCE_INDEX.md")
    assert "no-write evidence index" in doc
    assert "Phase 20 network transport evidence-index-only" in doc
    assert "does not create design closure records" in doc
    assert "does not record final approvals" in doc
    assert "does not start an implementation phase" in doc
    assert "does not create execution implementation" in doc
    assert "does not call interface execution methods" in doc
    assert "does not add a real bridge HTTP client" in doc
    assert "does not add network transport" in doc
    assert "does not open network sockets" in doc
    assert "does not call bridge POST endpoints" in doc
    assert "does not create design-freeze records" in doc
    assert "does not record operator signoffs" in doc
    assert "does not create cutover packets" in doc
    assert "does not capture bridge responses" in doc
    assert "does not create response capture records" in doc
    assert "does not set environment variables" in doc
    assert "does not create audit rows" in doc
    assert "does not mutate bridge state" in doc
    assert "does not call LACRM" in doc
    assert "Stage only the four Phase 21 Step 1 files" in doc
