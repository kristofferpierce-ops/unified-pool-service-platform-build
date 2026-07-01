from __future__ import annotations

import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd
import streamlit as st
from sqlmodel import Session

from app.core.database import engine
from app.services.cost_of_business import compute_cost_of_business, load_labor_settings
from app.services.estimator import LaborSettings
from app.services.expenses import list_expenses
from app.services.system_settings import set_setting

st.set_page_config(page_title='Cost of Doing Business', layout='wide')
st.title('True Cost of Doing Business')
st.caption('What one billable field hour actually costs us, fully loaded: burdened wages + every expense, '
           'amortized across real billable capacity. This is the floor every quote and route margin sits on.')

# --------------------------------------------------------------------------
# Inputs: start from stored labor settings, allow live what-if overrides.
# --------------------------------------------------------------------------
with Session(engine) as session:
    stored = load_labor_settings(session)
    expenses = list_expenses(session)

st.subheader('Labor inputs')
st.caption('These start from your saved labor settings. Adjust to model what-if scenarios; nothing is saved until you click Save.')
col1, col2, col3 = st.columns(3)
with col1:
    wage = st.number_input('Tech hourly wage ($)', min_value=0.0, value=float(stored.tech_hourly_wage), step=0.5)
    techs = st.number_input('Number of route techs', min_value=1, value=int(stored.number_of_route_techs), step=1)
with col2:
    payroll = st.number_input('Payroll tax burden (%)', min_value=0.0, value=float(stored.payroll_tax_burden_pct), step=0.5)
    billable = st.number_input('Billable hours / tech / year', min_value=1.0, value=float(stored.billable_hours_per_tech_per_year), step=50.0)
with col3:
    benefits = st.number_input('Benefits burden (%)', min_value=0.0, value=float(stored.benefits_burden_pct), step=0.5)
    target_margin = st.number_input('Target margin (%)', min_value=0.0, max_value=99.0, value=40.0, step=1.0,
                                    help='Margin as a percent of the sell price. Drives the break-even bill rate below.')

settings = LaborSettings(
    tech_hourly_wage=wage,
    payroll_tax_burden_pct=payroll,
    benefits_burden_pct=benefits,
    billable_hours_per_tech_per_year=billable,
    number_of_route_techs=int(techs),
)

with Session(engine) as session:
    cob = compute_cost_of_business(session, settings=settings, target_margin_pct=target_margin)

# --------------------------------------------------------------------------
# Headline numbers
# --------------------------------------------------------------------------
st.divider()
m1, m2, m3, m4 = st.columns(4)
m1.metric('True cost / billable hour', f'${cob.true_cost_per_hour:,.2f}',
          help='Burdened wage + overhead per billable hour. The real cost floor.')
m2.metric('Burdened wage / hour', f'${cob.burdened_wage_per_hour:,.2f}',
          help='Wage + payroll tax + benefits.')
m3.metric('Overhead / hour', f'${cob.overhead_per_hour:,.2f}',
          help='All annual expenses divided by annual billable capacity.')
m4.metric(f'Break-even @ {target_margin:.0f}% margin', f'${cob.break_even_bill_rate:,.2f}',
          help='Bill rate needed for one hour to hit the target margin.')

# --------------------------------------------------------------------------
# The cost stack
# --------------------------------------------------------------------------
st.subheader('Cost stack (per billable hour)')
stack_rows = []
running = 0.0
for label, amount in cob.stack:
    running += amount
    stack_rows.append({'Component': label, 'Per hour': round(amount, 2), 'Running total': round(running, 2)})
stack_rows.append({'Component': 'TRUE COST / HOUR', 'Per hour': round(cob.true_cost_per_hour, 2),
                   'Running total': round(cob.true_cost_per_hour, 2)})
st.dataframe(pd.DataFrame(stack_rows), width='stretch', hide_index=True)

# --------------------------------------------------------------------------
# Annual context + workers comp callout
# --------------------------------------------------------------------------
st.subheader('Annual context')
a1, a2, a3 = st.columns(3)
a1.metric('Annual billable capacity', f'{cob.annual_billable_capacity:,.0f} hrs',
          help='Billable hours/tech/year x number of route techs.')
a2.metric('Total annual overhead', f'${cob.annual_overhead_total:,.0f}',
          help='Sum of every ExpenseItem in Admin Costs.')
a3.metric('Workers comp / hour', f'${cob.workers_comp_per_hour:,.2f}',
          help=f'${cob.workers_comp_annual:,.0f}/yr in workers comp, amortized across billable capacity.')

if cob.workers_comp_annual == 0:
    st.info('No workers-comp line found in Admin Costs. Add an expense named "workers_comp" to call it out here.')

with st.expander('Expenses feeding overhead'):
    if expenses:
        exp_df = pd.DataFrame([
            {'Category': e.category, 'Name': e.name, 'Annual cost': round(e.annual_cost, 2)}
            for e in sorted(expenses, key=lambda x: (x.category, -x.annual_cost))
        ])
        st.dataframe(exp_df, width='stretch', hide_index=True)
        st.caption('Edit these on the Admin Costs page; changes flow straight into the cost per hour.')
    else:
        st.caption('No expenses recorded yet. Add them on the Admin Costs page.')

# --------------------------------------------------------------------------
# Persist the inputs as the saved labor settings
# --------------------------------------------------------------------------
st.divider()
if st.button('Save these labor settings', type='primary',
             help='Persist the inputs above as the labor settings used across estimating and cost calculations.'):
    with Session(engine) as session:
        set_setting(session, 'labor_settings', {
            'tech_hourly_wage': wage,
            'payroll_tax_burden_pct': payroll,
            'benefits_burden_pct': benefits,
            'billable_hours_per_tech_per_year': billable,
            'number_of_route_techs': int(techs),
        }, 'Labor settings saved from the Cost of Doing Business page.')
    st.success('Saved. These now drive estimating and every cost-per-hour calculation.')
