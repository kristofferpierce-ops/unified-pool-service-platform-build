from pathlib import Path


def test_streamlit_bridge_review_has_lacrm_candidate_controls():
    page = Path('ui/pages/14_Bridge_Review.py')
    assert page.exists()
    text = page.read_text(encoding='utf-8')
    assert 'build_lacrm_candidates_for_sms_thread' in text
    assert 'Search/import LACRM candidates' in text
    assert 'LACRM search terms' in text
