from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def test_bridge_routing_http_client_release_checkpoint_script_is_get_only() -> None:
    script = read("scripts/phase20_generate_bridge_routing_http_client_release_checkpoint.ps1")
    assert "phase20_bridge_routing_http_client_release_checkpoint_" in script
    assert "bridge_routing_http_client_release_checkpoint_only = $true" in script
    assert "bridge_get_only = $true" in script
    assert "platform_db_mutation_performed = $false" in script
    assert "bridge_mutation_performed = $false" in script
    assert "bridge_post_called = $false" in script
    assert "lacrm_call_performed = $false" in script
    assert "real_bridge_http_client_implemented = $false" in script
    assert "network_transport_implemented = $false" in script
    assert "bridge_post_call_implemented = $false" in script
    assert "routing_write_endpoint_implemented = $false" in script
    assert "can_execute_bridge_write_now = $false" in script
    assert "can_add_network_transport_now = $false" in script
    assert "can_add_real_bridge_http_client_now = $false" in script
    assert "phase20_bridge_routing_http_client_operator_signoff_*" in script
    assert "phase20_bridge_routing_http_client_preflight_matrix_*" in script
    assert "phase20_bridge_routing_http_client_dry_run_validation_*" in script
    assert "phase20_bridge_routing_http_client_dry_run_*" in script
    assert "phase20_bridge_routing_http_client_stub_*" in script
    assert "phase19_bridge_routing_write_release_checkpoint_*" in script
    assert "phase20_bridge_routing_http_client_release_checkpoint_artifacts.csv" in script
    assert "Get-FileHash" in script
    assert "Invoke-RestMethod" in script
    assert "Invoke-RestMethod -Method Post" not in script
    assert "Remove-Item" not in script
    assert "ConvertTo-Json -Depth 120" not in script


def test_bridge_routing_http_client_release_checkpoint_streamlit_page_is_report_only() -> None:
    page = read("ui/pages/58_Bridge_Routing_HTTP_Client_Release_Checkpoint.py")
    assert "Phase 20 Bridge Routing HTTP Client Release Checkpoint" in page
    assert "HTTP-client-release-checkpoint-only" in page
    assert "does not write to the bridge" in page
    assert "does not call bridge POST endpoints" in page
    assert "does not add network transport" in page
    assert "does not call LACRM" in page
    assert "phase20_bridge_routing_http_client_release_checkpoint_*" in page
    assert "phase20_bridge_routing_http_client_release_checkpoint.json" in page
    assert "requests.get" not in page
    assert "requests.post" not in page
    assert "st.download_button" in page


def test_bridge_routing_http_client_release_checkpoint_docs_capture_boundaries() -> None:
    doc = read("docs/PHASE20_STEP6_BRIDGE_ROUTING_HTTP_CLIENT_RELEASE_CHECKPOINT.md")
    assert "no-network release checkpoint" in doc
    assert "HTTP-client-release-checkpoint-only" in doc
    assert "bridge GET only" in doc
    assert "does not mutate bridge state" in doc
    assert "does not call LACRM" in doc
    assert "Do not stage generated release checkpoint reports" in doc
