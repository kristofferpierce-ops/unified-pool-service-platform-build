from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from datetime import date

import pandas as pd
import streamlit as st
from sqlmodel import Session, select

from ui._shared import configure_page, page_header
from app.core.database import create_db_and_tables, engine
from app.models.quote_tables import QuoteCase
from app.models.tables import Account, PoolVessel, Property
from app.services.accounts_receivable import accounts_receivable
from app.services.bootstrap import seed_defaults
from app.services.freshbooks_sync import get_freshbooks_mapping_summary
from app.services.lacrm_sync import get_lacrm_mapping_summary
from app.services.profitability import account_profitability, revenue_by_month, revenue_composition
from app.services.quote_workflow import get_dashboard_summary, list_quote_cases

configure_page('Unified Pool Service Operations Core', icon='🌊')

create_db_and_tables()
with Session(engine) as session:
    seed_defaults(session)
    accounts_count = len(list(session.exec(select(Account)).all()))
    properties_count = len(list(session.exec(select(Property)).all()))
    vessels_count = len(list(session.exec(select(PoolVessel)).all()))
    active_quotes = len(list(session.exec(select(QuoteCase)).all()))
    quote_dashboard = get_dashboard_summary(session)
    lacrm_summary = get_lacrm_mapping_summary(session)
    freshbooks_summary = get_freshbooks_mapping_summary(session)
    all_cases = list_quote_cases(session, limit=1000)
    sync_pending = sum(1 for case in all_cases if case.sync_status in {'local_only', 'pending_sync', 'pending_mapping', 'pending_contact_link', 'dry_run_ready', 'sync_failed'})
    sync_drift = sum(1 for case in all_cases if case.sync_status in {'drift', 'external_deleted'})

page_header(
    'Unified Pool Service Operations Core',
    'Operations dashboard shell for quoting, billing readiness, deliveries, front desk review, and modular estimating tools.',
    icon='🌊',
)

# --- Business at a glance: real FreshBooks revenue + A/R, front and center ---
_ytd_start = date(date.today().year, 1, 1)
with Session(engine) as _rev_session:
    _ytd = account_profitability(_rev_session, start=_ytd_start)
    _all_time = account_profitability(_rev_session)
    _comp_ytd = revenue_composition(_rev_session, start=_ytd_start)
    _ar = accounts_receivable(_rev_session)
    _monthly = revenue_by_month(_rev_session)

if _all_time.total_revenue > 0:
    st.subheader('Business at a glance')
    st.caption('Live FreshBooks billings and receivables. Cost and margin fill in once Skimmer actuals sync.')

    r1, r2, r3, r4, r5 = st.columns(5)
    r1.metric('Revenue YTD', f'${_ytd.total_revenue:,.0f}', help=f'FreshBooks invoices issued since {_ytd_start.isoformat()}.')
    r2.metric('Revenue all-time', f'${_all_time.total_revenue:,.0f}', help='Every FreshBooks invoice on record, all years.')
    r3.metric(
        'Recurring YTD',
        f'${_comp_ytd.recurring:,.0f}',
        help='Auto-paid (recurring autopay) share of this year\'s billings. The steady base under everything else.',
    )
    r4.metric(
        'Outstanding A/R',
        f'${_ar.total_outstanding:,.0f}',
        delta=f'${_ar.aged:,.0f} aged 31+' if _ar.aged else 'all current',
        delta_color='inverse',
        help=f'{_ar.invoice_count} uncollected invoices. Most autopay clears same-month, so A/R stays low.',
    )
    r5.metric('Customers', f'{len(_all_time.accounts):,}', help='Accounts with at least one invoice or logged visit.')

    trend_col, top_col = st.columns([3, 2])
    with trend_col:
        st.caption('Monthly billings (last 24 months)')
        if _monthly:
            _df = (
                pd.DataFrame(_monthly[-24:], columns=['Month', 'Revenue'])
                .set_index('Month')
            )
            st.bar_chart(_df, height=240, color='#2563eb')
        else:
            st.info('No dated invoices yet.')
    with top_col:
        st.caption('Top customers by revenue (all-time)')
        _top = [a for a in _all_time.accounts if a.revenue > 0][:8]
        if _top:
            st.dataframe(
                pd.DataFrame(
                    [{'Customer': a.name, 'Revenue': round(a.revenue, 2)} for a in _top]
                ),
                hide_index=True,
                width='stretch',
                column_config={'Revenue': st.column_config.NumberColumn(format='$%.0f')},
            )
        else:
            st.info('No customer revenue yet.')

    st.divider()

m1, m2, m3, m4, m5, m6, m7, m8, m9, m10 = st.columns(10)
m1.metric('Accounts', accounts_count, help='Total account records currently stored in the platform database.')
m2.metric('Properties', properties_count, help='Total property records currently stored in the platform database.')
m3.metric('Vessels', vessels_count, help='Total pool vessels currently stored in the platform database.')
m4.metric('Quote Cases', active_quotes, help='Total quote workflow cases currently tracked in the workflow ledger.')
m5.metric('Stale Cases', quote_dashboard['totals']['stale_cases'], help='Cases that have been in their current stage longer than the configured threshold.')
m6.metric('Follow Ups Due', quote_dashboard['totals']['follow_ups_due'], help='Cases with a follow up due date on or before today.')
m7.metric('LACRM Pending', sync_pending, help='Cases that still need mapping, contact linking, or a prepared sync before CRM alignment is complete.')
m8.metric('LACRM Drift', sync_drift, help='Cases where the CRM record was deleted or the webhook delivered a status that is not mapped locally yet.')
m9.metric('FB Drafts', freshbooks_summary['draft_prepared_count'], help='Quote cases with a FreshBooks draft prepared locally or live, waiting for review and send.')
m10.metric('FB Sent or Viewed', freshbooks_summary['sent_estimate_count'] + freshbooks_summary['viewed_estimate_count'], help='Quote cases whose linked FreshBooks estimate is already sent or viewed.')

st.subheader('Operations launchpad')
launch_a, launch_b, launch_c, launch_d = st.columns(4)
with launch_a:
    st.page_link('pages/11_Quote_Workflow.py', label='Quote Workflow', icon='🧭', help='Open the quote workflow board to create, review, sync, and move quote cases.')
    st.page_link('pages/7_Invoice_Review.py', label='Invoice Review', icon='🧾', help='Open the invoice review queue for staged invoice parsing and approval.')
    st.page_link('pages/00_Development.py', label='Development', icon='🧱', help='Open the development tracker: working features, code-health findings, and the improvement roadmap.')
with launch_b:
    st.page_link('pages/5_Commercial_Estimator.py', label='Commercial Estimator', icon='🏢', help='Open the commercial estimator for scenario building and pricing.')
    st.page_link('pages/4_Residential_Estimator.py', label='Residential Estimator', icon='🏠', help='Open the residential estimator for service pricing workflows.')
with launch_c:
    st.page_link('pages/6_Commercial_Deliveries.py', label='Commercial Deliveries', icon='🚚', help='Open monthly delivery reporting and property level billing review.')
    st.page_link('pages/9_Tools.py', label='Tools', icon='🛠️', help='Open operational tools such as property verification and future equipment quote modules.')
with launch_d:
    st.page_link('pages/18_Cost_of_Business.py', label='Cost of Business', icon='💵', help='Open the true cost-of-doing-business engine: fully-loaded cost per billable hour and break-even bill rates.')
    st.page_link('pages/19_Purchasing.py', label='Purchasing', icon='🛒', help='Open purchasing intelligence: best source per product, supplier price book, and price anomaly flags.')
    st.page_link('pages/20_Assets.py', label='Assets', icon='🧰', help='Open the asset registry: track equipment through ordered → received → installed → retired, with serial numbers and per-property asset lists.')
    st.page_link('pages/21_Skimmer.py', label='Skimmer Sync', icon='🌊', help='Pull Skimmer field-ops data (work orders, chemical logs, routes) into service visits with labor and chemical actuals.')
    st.page_link('pages/22_Customer_Matching.py', label='Customer Matching', icon='🔗', help='Reconcile Skimmer and FreshBooks customers into one account so cost and revenue join. Review and override matches here.')
    st.page_link('pages/23_Profitability.py', label='Profitability', icon='📈', help='Where the profit is: FreshBooks revenue minus real cost (labor + chemicals) per customer.')
    st.page_link('pages/27_Receivables.py', label='Receivables (A/R)', icon='💰', help='What customers owe, aged 0-30/31-60/61-90/90+, with a sortable collections list.')
    st.page_link('pages/24_Route_PnL.py', label='Route P&L', icon='🚚', help='Route-level profitability: which routes make money, which cost more, by route and technician.')
    st.page_link('pages/25_Variance.py', label='Variance', icon='🎯', help='Expected vs actual: priced visit time vs logged time, valued at true $/hour. Flags chronic overruns.')
    st.page_link('pages/26_Chemistry.py', label='Chemistry (LSI)', icon='🧪', help='Langelier water-balance index + dosing recommendations. Corrosive/balanced/scaling with fixes.')
    st.page_link('pages/8_Compare_&_Train.py', label='Compare + Train', icon='📊', help='Open compare and train workflows for pricing calibration and review.')
    st.page_link('pages/10_Estimate_Library.py', label='Estimate Library', icon='📚', help='Open saved estimate runs and exported reporting views.')
    st.page_link('pages/14_Bridge_Review.py', label='Bridge Review', icon='☎️', help='Open the platform-side bridge SMS review and guarded LACRM dry-run apply page.')

st.subheader('Quote workflow dashboard')
st.caption('These cards mirror the current CRM bucket language so staff can recognize the same workflow while the platform becomes the orchestration layer.')

pipeline_columns = st.columns(2)
for index, pipeline in enumerate(quote_dashboard['pipelines']):
    with pipeline_columns[index % 2]:
        with st.container(border=True):
            st.markdown(f"### {pipeline['pipeline_name']}")
            st.caption(f"Pipeline slug: `{pipeline['pipeline_slug']}`")
            for stage in pipeline['stages']:
                label = f"{stage['stage_name']}"
                counts = f"{stage['count']} total"
                extras: list[str] = []
                if stage['stale_count']:
                    extras.append(f"{stage['stale_count']} stale")
                if stage['follow_ups_due']:
                    extras.append(f"{stage['follow_ups_due']} due")
                if stage['sent_not_viewed']:
                    extras.append(f"{stage['sent_not_viewed']} sent not viewed")
                suffix = f" | {' | '.join(extras)}" if extras else ''
                st.write(f"**{label}:** {counts}{suffix}")

st.subheader('LACRM sync readiness')
st.caption('This section shows whether the local quote workflow stages have enough CRM mapping information to keep the program and the CRM aligned.')

sync_a, sync_b, sync_c = st.columns(3)
sync_a.metric(
    'Mapped Pipelines',
    f"{lacrm_summary['mapped_pipeline_count']} of {lacrm_summary['total_pipeline_count']}",
    help='How many internal pipeline families are matched to real LACRM pipeline ids.',
)
sync_b.metric(
    'Mapped Stages',
    f"{lacrm_summary['mapped_stage_count']} of {lacrm_summary['total_stage_count']}",
    help='How many internal stages are matched to real LACRM status ids.',
)
sync_c.metric(
    'Sync Mode',
    lacrm_summary['connection']['sync_mode'],
    help='Dry run means the app stores intended CRM actions without sending live writes. Live mode only turns on when you explicitly enable it and provide an API key.',
)

for pipeline in lacrm_summary['pipelines']:
    with st.expander(f"{pipeline['pipeline_name']} CRM map", expanded=False):
        st.write(f"**LACRM pipeline name:** {pipeline['lacrm_pipeline_name']}")
        st.write(f"**LACRM pipeline id:** {pipeline['lacrm_pipeline_id'] or 'Not mapped yet'}")
        for stage in pipeline['stages']:
            status_note = stage['lacrm_status_id'] or 'Missing status id'
            st.write(f"**{stage['stage_name']}:** {status_note}")

st.subheader('FreshBooks draft sync readiness')
st.caption('This section shows whether the draft estimate layer is configured to prepare local drafts only or can create and refresh real FreshBooks estimates through OAuth.')

fb_a, fb_b, fb_c, fb_d = st.columns(4)
fb_a.metric(
    'FreshBooks Mode',
    freshbooks_summary['connection']['sync_mode'],
    help='Dry run prepares draft payloads and review records locally. Live mode needs OAuth credentials and account context.',
)
fb_b.metric(
    'Access Token',
    'Present' if freshbooks_summary['connection']['has_access_token'] else 'Missing',
    help='FreshBooks uses OAuth 2.0 access tokens rather than API keys for accounting endpoints.',
)
fb_c.metric(
    'Account Id',
    'Present' if freshbooks_summary['connection']['has_account_id'] else 'Missing',
    help='Accounting endpoints need the FreshBooks account id. Context refresh can help resolve it from the identity endpoint when the token is valid.',
)
fb_d.metric(
    'Accepted or Invoiced',
    freshbooks_summary['accepted_estimate_count'],
    help='Quote cases whose linked FreshBooks estimate is already accepted or invoiced.',
)

for pipeline in freshbooks_summary['pipelines']:
    with st.expander(f"{pipeline['pipeline_name']} FreshBooks rules", expanded=False):
        st.write(f"**Enabled:** {'Yes' if pipeline['freshbooks_enabled'] else 'No'}")
        st.write(f"**Default currency:** {pipeline['default_currency_code']}")
        st.write(f"**Follow up stage:** {pipeline.get('follow_up_stage_slug') or 'Not configured'}")
        st.write(f"**Accepted stage:** {pipeline.get('accepted_stage_slug') or 'Not configured'}")

with st.expander('What this dashboard is becoming', expanded=False):
    st.write('Repo B is being turned into the workflow and quote orchestration layer that mirrors CRM stages, tracks case age, coordinates LACRM quote sync, and later will coordinate draft estimates in FreshBooks and live vendor pricing tools without forcing a full rebuild when workflow rules change.')

st.subheader('Equipment quote tools')
with Session(engine) as _heater_session:
    from app.services.heater_quote import get_heater_quote_dashboard_summary
    _heater_dashboard = get_heater_quote_dashboard_summary(_heater_session)

heater_metric_a, heater_metric_b, heater_metric_c = st.columns(3)
heater_metric_a.metric(
    'Heater Quote Runs',
    _heater_dashboard['total_runs'],
    help='Total heater sizing runs already saved inside the platform database.',
)
heater_metric_b.metric(
    'Heater Candidates',
    _heater_dashboard['candidate_count'],
    help='Total recommended heater candidates saved across all heater quote runs.',
)
heater_metric_c.metric(
    'Heritage Heater Mode',
    _heater_dashboard['heritage_connection']['sync_mode'],
    help='Dry run uses the fallback catalog. Live mode tries the configured Heritage catalog source first.',
)

st.page_link(
    'pages/12_Heater_Quote.py',
    label='Heater Quote Tool',
    icon='♨️',
    help='Click to size pool or spa heating, review recommended heaters, and attach a heater recommendation to an open quote case.',
)
