from pathlib import Path


def test_integration_health_page_documents_app_map_and_safety_controls():
    page = Path("ui/pages/15_Integration_Health.py")
    assert page.exists()

    text = page.read_text(encoding="utf-8")
    assert "Integration Health" in text
    assert "http://127.0.0.1:8501" in text
    assert "http://127.0.0.1:8010" in text
    assert "http://127.0.0.1:8000" in text
    assert "bridge_review_summary" in text
    assert "lacrm_apply_status" in text
    assert "lacrm_live_apply_readiness" in text
    assert "Live LACRM writes are OFF" in text
    assert "No live-applied action rows" in text
    assert "requests.get" in text
    assert "st.download_button" in text
