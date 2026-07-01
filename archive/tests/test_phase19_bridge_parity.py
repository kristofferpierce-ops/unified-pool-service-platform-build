from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def test_bridge_parity_generator_is_read_only_and_tracks_bridge_markers() -> None:
    script = read("scripts/phase19_generate_bridge_parity_matrix.ps1")
    assert "phase19_bridge_parity_matrix_" in script
    assert "Keys Pool Service Data Hub" in script
    assert "incomingHud" in script
    assert "Search LACRM" in script
    assert "runEodBtn" in script
    assert "original_bridge_data_hub" in script
    assert "Live write enabled" in script
    assert "Invoke-RestMethod" in script
    assert "Invoke-RestMethod -Method Post" not in script
    assert "Remove-Item" not in script


def test_bridge_parity_streamlit_page_reads_generated_matrix_only() -> None:
    page = read("ui/pages/21_Bridge_Parity.py")
    assert "Phase 19 Bridge Parity" in page
    assert "phase19_bridge_parity_matrix_*.json" in page
    assert "does not call LACRM" in page
    assert "does not mutate platform data" in page
    assert "does not patch the bridge" in page
    assert "st.dataframe" in page
    assert "requests.get" not in page
    assert "requests.post" not in page


def test_bridge_parity_docs_capture_guardrails() -> None:
    doc = read("docs/PHASE19_STEP19_BRIDGE_PARITY.md")
    assert "original KPS Bridge / Data Hub remains the operational UI" in doc
    assert "does not call LACRM" in doc
    assert "Do not stage generated parity outputs" in doc
