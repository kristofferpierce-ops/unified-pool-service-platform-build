from pathlib import Path


def test_streamlit_bridge_review_has_step10_live_readiness_controls():
    page = Path('ui/pages/14_Bridge_Review.py')
    assert page.exists()
    text = page.read_text(encoding='utf-8')
    assert 'lacrm_live_apply_readiness' in text
    assert 'Live Armed' in text
    assert 'Type live confirmation phrase' in text
    assert 'Step 10 live gate' in text
    assert 'live_confirmation_phrase' in text
