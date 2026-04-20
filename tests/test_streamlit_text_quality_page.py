from pathlib import Path


def test_text_quality_streamlit_page_contains_display_only_safety_copy():
    page = Path('ui/pages/16_Text_Quality.py').read_text(encoding='utf-8')
    assert 'Text Quality Workbench' in page
    assert 'display-only' in page
    assert 'list_text_quality_samples' in page
    assert 'text_quality_summary' in page
    assert 'does not mutate raw' in page or 'does not rewrite' in page
