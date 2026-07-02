from __future__ import annotations

import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pandas as pd
import streamlit as st
from sqlmodel import select

from ui._shared import configure_page, db_session, page_header, section
from app.models.customer_tables import CustomerProfile
from app.services.customer_matching import (
    confirm_match,
    list_matches,
    matching_summary,
    merge_account,
    unlink_match,
)

configure_page('Customer Matching', icon='🔗')
page_header(
    'Customer Matching',
    'Reconciles external customer records (Skimmer, FreshBooks) into one account so cost and revenue '
    'join. Everything auto-attributes: exact email/phone or strong name auto-links; anything ambiguous '
    'still gets its own account (so no revenue is orphaned) but is flagged below as a possible duplicate '
    'you can merge whenever you like. Nothing here ever blocks your numbers.',
    icon='🔗',
)

STATUS_BADGE = {'auto': '🟢', 'confirmed': '✅', 'flagged': '🟠', 'suggested': '🟡', 'unmatched': '🔴'}


def _account_options(session) -> dict:
    profiles = list(session.exec(select(CustomerProfile)).all())
    return {p.account_id: (p.company_name or p.display_name or f'Account {p.account_id}') for p in profiles}


with db_session() as session:
    summary = matching_summary(session)
    account_opts = _account_options(session)

m1, m2, m3, m4 = st.columns(4)
m1.metric('Customer accounts', summary['accounts'])
m2.metric('Matches recorded', summary['total'])
m3.metric('Possible duplicates', summary.get('possible_duplicates', 0),
          help='Auto-attributed but similar to another account — optional to review/merge. Never blocks your numbers.')
m4.metric('Blocking (orphaned)', summary['needs_review'],
          help='Records with no account at all. Should be ~0 under auto-attribute.')

# --------------------------------------------------------------------------
# Possible duplicates (auto-attributed, optional review) — YOUR REVIEW SURFACE
# --------------------------------------------------------------------------
with db_session() as session:
    flagged = [m for m in list_matches(session) if m.status == 'flagged']

if flagged:
    section('Possible duplicates — review anytime',
            'These customers were auto-given their own account (so their revenue counts), but they look '
            'similar to an existing account. Keep them separate, or merge if they are the same customer. '
            'No rush — nothing here affects your totals.')
    st.caption(f'{len(flagged)} flagged. Work through these whenever you feel like it; they persist until you decide.')
    for m in flagged[:100]:
        cands = json.loads(m.candidates_json or '[]')
        with st.container(border=True):
            st.markdown(f"🟠 **{m.external_name or '(no name)'}** · {m.source_slug} · "
                        f"{m.external_email or 'no email'}")
            if cands:
                st.caption('Looks like: ' + ', '.join(f"{c['name']} ({int(c['score']*100)}%)" for c in cands))
            cols = st.columns([2, 1, 1])
            with cols[0]:
                merge_target = st.selectbox(
                    'Merge into', options=[c['account_id'] for c in cands],
                    format_func=lambda i: account_opts.get(i, f'Account {i}'), key=f'mt_{m.id}'
                ) if cands else None
            with cols[1]:
                st.write('')
                if cands and st.button('Merge', key=f'merge_{m.id}', type='primary'):
                    with db_session() as session:
                        merge_account(session, m.account_id, merge_target)
                    st.success('Merged.')
                    st.rerun()
            with cols[2]:
                st.write('')
                if st.button('Keep separate', key=f'keep_{m.id}'):
                    with db_session() as session:
                        confirm_match(session, m.id, m.account_id)
                    st.success('Kept separate.')
                    st.rerun()

if summary['total'] == 0:
    st.info('No matches yet. Run a Skimmer sync (and later a FreshBooks pull) — external customers resolve '
            'to accounts automatically, and anything ambiguous lands here for review.')

# --------------------------------------------------------------------------
# Manual review queue
# --------------------------------------------------------------------------
with db_session() as session:
    queue = [m for m in list_matches(session) if m.status in ('suggested', 'unmatched')]

if queue:
    section('Review queue', 'Ambiguous or unmatched external records. Link each to the right account.')
    for m in queue:
        with st.container(border=True):
            st.markdown(f"{STATUS_BADGE.get(m.status, '')} **{m.external_name or '(no name)'}** "
                        f"· {m.source_slug} · {m.external_email or 'no email'} · {m.external_phone or 'no phone'}")
            candidates = json.loads(m.candidates_json or '[]')
            if candidates:
                st.caption('Suggested matches: ' + ', '.join(
                    f"{c['name']} ({int(c['score'] * 100)}%)" for c in candidates))
            cols = st.columns([3, 1])
            with cols[0]:
                default_ids = [c['account_id'] for c in candidates if c['account_id'] in account_opts]
                options = list(account_opts.keys())
                idx = options.index(default_ids[0]) if default_ids and default_ids[0] in options else 0
                chosen = st.selectbox('Link to account', options=options,
                                      format_func=lambda i: account_opts.get(i, f'Account {i}'),
                                      index=idx if options else 0, key=f'link_{m.id}') if options else None
            with cols[1]:
                st.write('')
                if options and st.button('Confirm link', key=f'confirm_{m.id}', type='primary'):
                    with db_session() as session:
                        confirm_match(session, m.id, chosen)
                    st.success('Linked.')
                    st.rerun()
else:
    if summary['total'] > 0:
        st.success('Review queue is clear — every external customer is resolved to an account.')

# --------------------------------------------------------------------------
# All matches + override
# --------------------------------------------------------------------------
with db_session() as session:
    all_matches = list_matches(session)

if all_matches:
    section('All matches')
    st.dataframe(pd.DataFrame([{
        'Status': f"{STATUS_BADGE.get(m.status, '')} {m.status}",
        'Source': m.source_slug,
        'External': m.external_name,
        'Email': m.external_email,
        'Account': account_opts.get(m.account_id, '—') if m.account_id else '—',
        'Pass': m.match_pass,
        'Conf': round(m.confidence, 2),
    } for m in all_matches]), width='stretch', hide_index=True)

    with st.expander('Override a match (relink or unlink)'):
        linked = [m for m in all_matches if m.account_id]
        if linked:
            label = {f"#{m.id} {m.external_name} → {account_opts.get(m.account_id, m.account_id)}": m for m in linked}
            pick = st.selectbox('Match', options=list(label.keys()))
            chosen_match = label[pick]
            oc = st.columns([3, 1, 1])
            with oc[0]:
                new_acct = st.selectbox('Relink to', options=list(account_opts.keys()),
                                        format_func=lambda i: account_opts.get(i, f'Account {i}'), key='override_acct')
            with oc[1]:
                st.write('')
                if st.button('Relink', key='override_relink'):
                    with db_session() as session:
                        confirm_match(session, chosen_match.id, new_acct)
                    st.success('Relinked.')
                    st.rerun()
            with oc[2]:
                st.write('')
                if st.button('Unlink', key='override_unlink'):
                    with db_session() as session:
                        unlink_match(session, chosen_match.id)
                    st.success('Unlinked — back in the queue.')
                    st.rerun()
        else:
            st.caption('No linked matches to override yet.')
