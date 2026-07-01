"""Shared UI helpers for the Streamlit app.

One place for the page chrome so every page looks the same: consistent
set_page_config, a small CSS refinement layered on top of the global theme
(.streamlit/config.toml), a uniform page header, and a DB-session context
manager. This retires the copy-pasted boilerplate that used to live at the top
of every page.

Usage (top of a page):

    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # parents[1] from ui/Dashboard.py
    from ui._shared import configure_page, page_header, section, db_session

    configure_page('Cost of Doing Business', icon='💵')
    page_header('True Cost of Doing Business', 'What one billable hour really costs.', icon='💵')
"""
from __future__ import annotations

from contextlib import contextmanager
from datetime import date, timedelta
from typing import Iterator

import streamlit as st

# CSS refinement on top of the config.toml theme. Targets stable data-testid
# selectors so it survives Streamlit upgrades. Emitted every run (a <style>
# block must be present in the DOM on each render).
_REFINEMENT_CSS = """
<style>
  .block-container { padding-top: 2.1rem; padding-bottom: 3rem; max-width: 1320px; }
  h1 { font-weight: 700; letter-spacing: -0.02em; }
  h2, h3 { font-weight: 640; letter-spacing: -0.01em; }

  /* Metric widgets styled as clean stat cards (echoes Lumen's stat row). */
  [data-testid="stMetric"] {
    background: #F1F5F7;
    border: 1px solid rgba(14, 124, 134, 0.16);
    border-radius: 10px;
    padding: 12px 16px;
  }
  [data-testid="stMetricLabel"] p {
    font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.05em;
    color: #5B6B76; font-weight: 600;
  }
  [data-testid="stMetricValue"] { font-size: 1.6rem; font-weight: 700; }

  /* Tighter tab row + dividers. */
  [data-baseweb="tab-list"] { gap: 2px; }
  hr { margin: 0.9rem 0; }
</style>
"""


def configure_page(title: str, icon: str | None = None, layout: str = 'wide') -> None:
    """Set page config once and inject the shared CSS refinement.

    Must be the first Streamlit call on a page (set_page_config requirement).
    """
    st.set_page_config(page_title=title, page_icon=icon, layout=layout)
    st.markdown(_REFINEMENT_CSS, unsafe_allow_html=True)


def page_header(title: str, caption: str | None = None, icon: str | None = None) -> None:
    """Uniform page title + optional caption."""
    st.title(f'{icon} {title}' if icon else title)
    if caption:
        st.caption(caption)


def section(title: str, caption: str | None = None) -> None:
    """Uniform section subheader + optional caption."""
    st.subheader(title)
    if caption:
        st.caption(caption)


def date_range_selector(key: str, label: str = 'Period',
                        default: str = 'Year to date') -> tuple[date | None, date | None]:
    """A period picker returning (start, end) inclusive dates, or (None, None) for
    all-time. Presets (7 day / 30 day / YTD first) plus a custom range."""
    today = date.today()
    presets = {
        'Last 7 days': (today - timedelta(days=7), today),
        'Last 30 days': (today - timedelta(days=30), today),
        'Year to date': (date(today.year, 1, 1), today),
        'This month': (date(today.year, today.month, 1), today),
        'Last 12 months': (today - timedelta(days=365), today),
        'All time': (None, None),
        'Custom…': 'custom',
    }
    keys = list(presets.keys())
    index = keys.index(default) if default in presets else 0
    choice = st.selectbox(label, options=keys, index=index, key=f'{key}_preset')
    value = presets[choice]
    if value == 'custom':
        c1, c2 = st.columns(2)
        start = c1.date_input('From', value=today - timedelta(days=90), key=f'{key}_from')
        end = c2.date_input('To', value=today, key=f'{key}_to')
        return start, end
    return value


@contextmanager
def db_session() -> Iterator['object']:
    """Context-managed SQLModel session bound to the app engine.

    Replaces the ad-hoc `with Session(engine)` blocks copy-pasted across pages.
    """
    from sqlmodel import Session

    from app.core.database import engine

    session = Session(engine)
    try:
        yield session
    finally:
        session.close()
