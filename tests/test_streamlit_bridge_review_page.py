from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_streamlit_bridge_review_page_exists_and_uses_platform_services():
    page = ROOT / 'ui' / 'pages' / '14_Bridge_Review.py'
    assert page.exists()
    text = page.read_text(encoding='utf-8')
    assert 'bridge_review_summary' in text
    assert 'apply_sms_thread_to_lacrm' in text
    assert 'build_sms_thread_lacrm_apply_plan' in text
    assert 'http://127.0.0.1:8000' in text
    assert 'Dry run' in text


def test_dashboard_links_to_bridge_review_page():
    dashboard = ROOT / 'ui' / 'Dashboard.py'
    text = dashboard.read_text(encoding='utf-8')
    assert "pages/14_Bridge_Review.py" in text
    assert "Bridge Review" in text
