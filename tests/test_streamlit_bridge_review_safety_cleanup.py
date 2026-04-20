from pathlib import Path


def test_streamlit_bridge_review_safety_cleanup_markers_present():
    page = Path('ui/pages/14_Bridge_Review.py').read_text(encoding='utf-8')

    assert 'LIVE LACRM WRITES ARE OFF / BLOCKED BY DEFAULT' in page
    assert 'Raw safety JSON for debugging/export' in page
    assert 'Hide synthetic Phase 19 test actions' in page
    assert 'Raw apply-action JSON' in page
    assert 'Raw audit export preview' in page
    assert '_render_safety_cards' in page
    assert '_is_synthetic_apply_action' in page
    assert 'st.json(lacrm_status)' not in page


def test_streamlit_bridge_review_safety_cleanup_does_not_change_ports():
    page = Path('ui/pages/14_Bridge_Review.py').read_text(encoding='utf-8')

    assert 'http://127.0.0.1:8000' in page
    assert 'port 8000' in page
