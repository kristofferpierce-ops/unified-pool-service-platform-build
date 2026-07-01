from pathlib import Path


def test_streamlit_bridge_review_has_lacrm_apply_audit_controls():
    page = Path('ui/pages/14_Bridge_Review.py')
    assert page.exists()
    text = page.read_text(encoding='utf-8')
    assert 'Apply Audit' in text
    assert 'lacrm_apply_readiness' in text
    assert 'list_crm_apply_actions' in text
    assert 'get_crm_apply_action_detail' in text
    assert 'Download apply audit JSON' in text
