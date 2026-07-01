from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def test_call_context_snapshot_generator_is_read_only() -> None:
    script = read("scripts/phase19_generate_call_context_snapshot.ps1")
    assert "phase19_call_context_snapshot_" in script
    assert "Keys Pool Service Data Hub" in script
    assert "incomingHud" in script
    assert "/api/calls?view=active" in script
    assert "/api/calls?view=processed" in script
    assert "bridge_mutation_performed = $false" in script
    assert "lacrm_call_performed = $false" in script
    assert "Invoke-RestMethod" in script
    assert "Invoke-RestMethod -Method Post" not in script
    assert "Remove-Item" not in script


def test_call_context_streamlit_page_warns_read_only() -> None:
    page = read("ui/pages/22_Call_Context.py")
    assert "Phase 19 Call Context" in page
    assert "read-only" in page.lower()
    assert "does not call LACRM" in page
    assert "does not modify bridge state" in page
    assert "/api/calls?view=active" in page
    assert "Keys Pool Service Data Hub" in page
    assert "incomingHud" in page
    assert "requests.get" in page
    assert "requests.post" not in page
    assert "st.download_button" in page


def test_call_context_docs_capture_bridge_boundaries() -> None:
    doc = read("docs/PHASE19_STEP20_CALL_CONTEXT.md")
    assert "incoming call/HUD context" in doc
    assert "does not call LACRM" in doc
    assert "does not mutate bridge state" in doc
    assert "original KPS Bridge / Data Hub UI" in doc

def test_call_context_page_handles_none_transcript_preview() -> None:
    page = read("ui/pages/22_Call_Context.py")
    assert 'item.get("transcript") or ""' in page
    assert "str(summary)[:120]" in page
