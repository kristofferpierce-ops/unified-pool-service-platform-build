from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def test_eod_snapshot_generator_is_read_only() -> None:
    script = read("scripts/phase19_generate_eod_sms_snapshot.ps1")
    assert "phase19_eod_sms_snapshot_" in script
    assert "runEodBtn" in script
    assert "Text summaries" in script
    assert "forceBatchBtn" in script
    assert "/api/sms/batches?view=active" in script
    assert "/api/sms/batches?view=processed" in script
    assert "bridge_batch_mutation_performed = $false" in script
    assert "bridge_force_batch_called = $false" in script
    assert "bridge_run_eod_called = $false" in script
    assert "Invoke-RestMethod" in script
    assert "Invoke-RestMethod -Method Post" not in script
    assert "Remove-Item" not in script


def test_eod_streamlit_page_warns_read_only() -> None:
    page = read("ui/pages/23_EOD_SMS_Batches.py")
    assert "Phase 19 EOD SMS Batches" in page
    assert "read-only" in page.lower()
    assert "does not press the bridge Run EOD button" in page
    assert "does not force rebuild batches" in page
    assert "does not call LACRM" in page
    assert "/api/sms/batches?view=active" in page
    assert "/api/sms/batches?view=processed" in page
    assert "requests.get" in page
    assert "requests.post" not in page
    assert "st.download_button" in page


def test_eod_docs_capture_bridge_boundaries() -> None:
    doc = read("docs/PHASE19_STEP21_EOD_SMS.md")
    assert "end-of-day SMS batch workflow" in doc
    assert "does not call LACRM" in doc
    assert "does not mutate bridge state" in doc
    assert "does not force SMS batch rebuilds" in doc
    assert "original KPS Bridge / Data Hub UI" in doc
