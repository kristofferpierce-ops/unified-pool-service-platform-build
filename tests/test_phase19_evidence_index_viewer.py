from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def test_evidence_index_page_is_read_only_and_uses_extractor_pack() -> None:
    page = read("ui/pages/19_Evidence_Index.py")
    assert "Phase 19 Evidence Index" in page
    assert "phase19_extractor_evidence_*" in page
    assert "phase19_evidence_index.json" in page
    assert "phase19_redacted_checkpoint.json" in page
    assert "requests.post" not in page
    assert "requests.get" not in page
    assert "st.download_button" in page
    assert "Phone leak check" in page
    assert "Email leak check" in page


def test_evidence_pack_verifier_is_read_only() -> None:
    script = read("scripts/phase19_verify_evidence_pack.ps1")
    assert "phase19_extractor_evidence_*" in script
    assert "phase19_evidence_index.json" in script
    assert "phase19_redacted_checkpoint.json" in script
    assert "PASS | evidence=" in script
    assert "Invoke-RestMethod" not in script
    assert "Set-Content" not in script
    assert "Remove-Item" not in script


def test_evidence_index_docs_capture_boundaries() -> None:
    doc = read("docs/PHASE19_STEP17_EVIDENCE_INDEX_VIEWER.md")
    assert "platform owns business/workflow state" in doc
    assert "bridge remains the original Data Hub" in doc
    assert "extractor owns evidence/governance/replay artifacts" in doc
    assert "Do not stage generated evidence packs" in doc
