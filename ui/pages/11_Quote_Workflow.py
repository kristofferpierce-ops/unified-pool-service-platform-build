from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd
import streamlit as st
from sqlmodel import Session, select

from app.core.database import create_db_and_tables, engine
from app.models.tables import Account, Property
from app.services.bootstrap import seed_defaults
from app.services.lacrm_sync import (
    get_case_lacrm_summary,
    get_lacrm_mapping_summary,
    link_quote_case_to_lacrm_contact,
    refresh_lacrm_mapping_from_api,
    sync_quote_case_to_lacrm,
)
from app.services.freshbooks_sync import (
    get_case_freshbooks_summary,
    get_freshbooks_mapping_summary,
    link_quote_case_to_freshbooks_client,
    mark_quote_case_freshbooks_sent,
    refresh_freshbooks_context_from_api,
    refresh_quote_case_from_freshbooks,
    sync_quote_case_to_freshbooks,
)
from app.services.heater_quote import get_quote_case_heater_package_workspace, remove_heater_package_from_quote_case, reset_heater_package_lines, update_heater_package_lines
from app.services.quote_workflow import (
    create_quote_case,
    get_dashboard_summary,
    get_quote_workflow_config,
    list_quote_cases,
    list_stage_options,
    move_quote_case,
    serialize_quote_case,
)

st.set_page_config(page_title='Quote Workflow', layout='wide')

create_db_and_tables()
with Session(engine) as session:
    seed_defaults(session)
    workflow_config = get_quote_workflow_config(session)
    account_options = list(session.exec(select(Account).order_by(Account.name)).all())
    property_options = list(session.exec(select(Property).order_by(Property.name)).all())
    dashboard = get_dashboard_summary(session)
    lacrm_summary = get_lacrm_mapping_summary(session)
    freshbooks_summary = get_freshbooks_mapping_summary(session)

pipeline_options = workflow_config.get('pipelines', [])
pipeline_lookup = {item['slug']: item for item in pipeline_options}

st.title('Quote Workflow')
st.caption('Create quote cases, move them across the mirrored CRM buckets, link them to the correct CRM contact, and prepare or run CRM sync from one place.')

summary_a, summary_b, summary_c, summary_d, summary_e, summary_f = st.columns(6)
summary_a.metric('Open Cases', dashboard['totals']['open_cases'], help='Cases that are not in a closed stage.')
summary_b.metric('Stale Cases', dashboard['totals']['stale_cases'], help='Cases that have sat in their current stage longer than the configured threshold.')
summary_c.metric('Follow Ups Due', dashboard['totals']['follow_ups_due'], help='Cases with a follow up date due today or earlier.')
summary_d.metric('Sent Not Viewed', dashboard['totals']['sent_not_viewed'], help='Cases in sent style stages that have not yet been marked viewed.')
summary_e.metric('Mapped Stages', f"{lacrm_summary['mapped_stage_count']} / {lacrm_summary['total_stage_count']}", help='How many internal stages are already matched to real LACRM status ids.')
summary_f.metric('Sync Mode', lacrm_summary['connection']['sync_mode'], help='Dry run stores the intended CRM actions safely. Live mode only runs when you explicitly enable it and provide an API key.')

with st.expander('LACRM sync controls', expanded=False):
    st.write('Use this area to check whether the CRM mapping is ready. Refresh uses read-only API calls. Case level sync buttons below will stay in dry run mode unless live mode is explicitly enabled.')
    control_a, control_b = st.columns(2)
    control_a.write(f"**API key present:** {'Yes' if lacrm_summary['connection']['has_api_key'] else 'No'}")
    control_a.write(f"**API base URL:** {lacrm_summary['connection']['api_base_url']}")
    control_b.write(f"**Mapped pipelines:** {lacrm_summary['mapped_pipeline_count']} of {lacrm_summary['total_pipeline_count']}")
    control_b.write(f"**Mapped stages:** {lacrm_summary['mapped_stage_count']} of {lacrm_summary['total_stage_count']}")
    if st.button('Refresh mapping from LACRM', help='Read the live pipeline and status names from LACRM and fill in any matching ids without changing your local quote stages.'):
        with Session(engine) as session:
            try:
                refresh_lacrm_mapping_from_api(session)
                st.success('LACRM mapping refresh completed.')
            except ValueError as exc:
                st.error(str(exc))
        st.rerun()
    for pipeline in lacrm_summary['pipelines']:
        with st.expander(f"{pipeline['pipeline_name']} mapping", expanded=False):
            st.write(f"**LACRM pipeline name:** {pipeline['lacrm_pipeline_name']}")
            st.write(f"**LACRM pipeline id:** {pipeline['lacrm_pipeline_id'] or 'Missing'}")
            for stage in pipeline['stages']:
                stage_status = stage['lacrm_status_id'] or 'Missing status id'
                st.write(f"**{stage['stage_name']}:** {stage_status}")

with st.expander('FreshBooks draft sync controls', expanded=False):
    st.write('FreshBooks uses OAuth rather than an API key. Draft preparation is safe to use in dry run mode even before OAuth is configured. Live draft creation and live status refresh only work after the access token and account id are available.')
    fb_control_a, fb_control_b = st.columns(2)
    fb_control_a.write(f"**Access token present:** {'Yes' if freshbooks_summary['connection']['has_access_token'] else 'No'}")
    fb_control_a.write(f"**Account id present:** {'Yes' if freshbooks_summary['connection']['has_account_id'] else 'No'}")
    fb_control_b.write(f"**Drafts prepared:** {freshbooks_summary['draft_prepared_count']}")
    fb_control_b.write(f"**Sent or viewed:** {freshbooks_summary['sent_estimate_count'] + freshbooks_summary['viewed_estimate_count']}")
    if st.button('Refresh FreshBooks context', help='Call the FreshBooks identity endpoint to confirm OAuth access and help resolve account context for accounting endpoints.'):
        with Session(engine) as session:
            try:
                refresh_freshbooks_context_from_api(session)
                st.success('FreshBooks context refresh completed.')
            except ValueError as exc:
                st.error(str(exc))
        st.rerun()

with st.expander('Create new quote case', expanded=True):
    with st.form('create_quote_case_form', clear_on_submit=True):
        c1, c2 = st.columns(2)
        selected_pipeline_slug = c1.selectbox(
            'Pipeline',
            options=[item['slug'] for item in pipeline_options],
            format_func=lambda slug: pipeline_lookup[slug]['name'],
            help='Select the workflow bucket family that should own this quote request.',
        )
        stage_choices = list_stage_options(workflow_config, selected_pipeline_slug)
        selected_stage_slug = c2.selectbox(
            'Starting stage',
            options=[item['slug'] for item in stage_choices],
            index=0,
            format_func=lambda slug: next(stage['name'] for stage in stage_choices if stage['slug'] == slug),
            help='Choose the starting stage. Most new requests should begin in Info + Costing.',
        )
        title = st.text_input('Case title', help='Use a short title that makes the request obvious at a glance.')
        d1, d2, d3 = st.columns(3)
        requester_name = d1.text_input('Requester name', help='Customer or caller name tied to this quote request.')
        requester_phone = d2.text_input('Requester phone', help='Primary phone number for follow up and CRM matching.')
        requester_email = d3.text_input('Requester email', help='Primary email for FreshBooks estimate delivery later.')
        e1, e2 = st.columns(2)
        selected_account_name = e1.selectbox(
            'Account',
            options=[''] + [account.name for account in account_options],
            help='Optional internal account link for known customers or associations.',
        )
        selected_property_name = e2.selectbox(
            'Property',
            options=[''] + [prop.name for prop in property_options],
            help='Optional property link for requests tied to a specific property.',
        )
        description = st.text_area('Request description', help='Add internal context, notes from the caller, or pricing instructions here.')
        assigned_to = st.text_input('Assigned to', help='Optional staff owner name or initials for quick queue ownership.')
        if st.form_submit_button('Create quote case', help='Create a new local quote case in the selected starting bucket.'):
            if not title.strip():
                st.error('Case title is required.')
            else:
                account_id = next((account.id for account in account_options if account.name == selected_account_name), None)
                property_id = next((prop.id for prop in property_options if prop.name == selected_property_name), None)
                with Session(engine) as session:
                    case = create_quote_case(
                        session,
                        pipeline_slug=selected_pipeline_slug,
                        stage_slug=selected_stage_slug,
                        title=title.strip(),
                        requester_name=requester_name.strip(),
                        requester_phone=requester_phone.strip(),
                        requester_email=requester_email.strip(),
                        account_id=account_id,
                        property_id=property_id,
                        description=description.strip(),
                        assigned_to=assigned_to.strip(),
                    )
                st.success(f'Created {case.quote_number} in {selected_pipeline_slug}.')
                st.rerun()

st.subheader('Case queue')
filter_a, filter_b, filter_c = st.columns(3)
selected_pipeline_filter = filter_a.selectbox(
    'Filter by pipeline',
    options=['all'] + [item['slug'] for item in pipeline_options],
    format_func=lambda slug: 'All pipelines' if slug == 'all' else pipeline_lookup[slug]['name'],
    help='Limit the queue to a single pipeline when you want to work one bucket at a time.',
)
selected_stage_filter = filter_b.text_input('Filter by stage slug', help='Optional exact stage slug filter such as quoting or follow_up.')
include_closed = filter_c.checkbox('Include closed cases', value=False, help='Show closed cases when you need historical context.')

with Session(engine) as session:
    cases = list_quote_cases(
        session,
        pipeline_slug=None if selected_pipeline_filter == 'all' else selected_pipeline_filter,
        stage_slug=selected_stage_filter.strip() or None,
        include_closed=include_closed,
        limit=200,
    )
    serialized_cases = [serialize_quote_case(session, case, workflow_config) for case in cases]

if not serialized_cases:
    st.info('No quote cases match the current filters yet.')
else:
    for case in serialized_cases:
        stage_choices = list_stage_options(workflow_config, case['pipeline_slug'])
        allowed_stage_labels = {stage['slug']: stage['name'] for stage in stage_choices}
        with st.container(border=True):
            row1, row2, row3 = st.columns([2, 2, 2])
            row1.markdown(f"### {case['quote_number']} | {case['title']}")
            row1.caption(f"{case['pipeline_name']} | {case['stage_name']}")
            row2.metric('Age', f"{case['age_days']} days", help='Total days since the quote case was created.')
            row2.metric('Stage Age', f"{case['stage_age_days']} days", help='Days spent in the current stage.')
            viewed_label = 'Yes' if case['is_viewed'] else 'No'
            row3.metric('Viewed', viewed_label, help='Quick glance indicator showing whether the quote has been marked viewed yet.')
            detail_a, detail_b, detail_c = st.columns([2, 2, 2])
            detail_a.write(f"**Requester:** {case['requester_name'] or 'Unknown'}")
            detail_a.write(f"**Phone:** {case['requester_phone'] or 'Not set'}")
            detail_b.write(f"**Follow Up Due:** {case['follow_up_due_on'] or 'Not set'}")
            detail_b.write(f"**FreshBooks Status:** {case['freshbooks_status']}")
            detail_c.write(f"**Sync Status:** {case['sync_status']}")
            detail_c.write(f"**Assigned To:** {case['assigned_to'] or 'Unassigned'}")
            if case['description']:
                st.write(case['description'])

            with Session(engine) as session:
                lacrm_case_summary = get_case_lacrm_summary(session, case['id'])
                freshbooks_case_summary = get_case_freshbooks_summary(session, case['id'])
                heater_package_workspace = get_quote_case_heater_package_workspace(session, case['id'])

            lacrm_links = lacrm_case_summary
            freshbooks_links = freshbooks_case_summary
            st.caption(
                ' | '.join(
                    [
                        f"LACRM contact: {lacrm_links['contact_link']['external_id'] if lacrm_links['contact_link'] else 'Not linked'}",
                        f"Pipeline item: {lacrm_links['pipeline_item_link']['external_id'] if lacrm_links['pipeline_item_link'] else 'Not linked'}",
                        f"Follow up task: {lacrm_links['follow_up_task_link']['external_id'] if lacrm_links['follow_up_task_link'] else 'Not linked'}",
                    ]
                )
            )
            if lacrm_links['blockers']:
                st.warning(' '.join(lacrm_links['blockers']))

            st.caption(
                ' | '.join(
                    [
                        f"FreshBooks client: {freshbooks_links['client_link']['external_id'] if freshbooks_links['client_link'] else 'Not linked'}",
                        f"Estimate: {freshbooks_links['estimate_link']['external_id'] if freshbooks_links['estimate_link'] else 'Not linked'}",
                        f"Estimate state: {freshbooks_links['local_estimate_state']['ui_status'] or 'Not prepared'}",
                    ]
                )
            )
            if freshbooks_links['blockers']:
                st.info(' '.join(freshbooks_links['blockers']))

            package_metric_a, package_metric_b = st.columns(2)
            package_metric_a.metric(
                'Attached Packages',
                heater_package_workspace['package_count'],
                help='How many equipment packages are currently attached to this quote case.',
            )
            package_metric_b.metric(
                'Package Total',
                f"{heater_package_workspace['grand_total']:,.2f} {heater_package_workspace['currency_code']}",
                help='Total of all attached equipment, material, allowance, and labor package lines currently linked to this quote case.',
            )

            with st.expander(f"Attached equipment packages for {case['quote_number']}", expanded=False):
                if not heater_package_workspace['packages']:
                    st.caption('No equipment packages are attached yet. Use the Heater Quote Tool to attach a package, or replace an existing package from there later.')
                else:
                    st.caption(f"Use the Heater Quote Tool with quote case {case['id']} if you want to replace the current package set.")
                    for package in heater_package_workspace['packages']:
                        pkg_candidate = package.get('candidate', {})
                        pkg_summary = package.get('package_summary', {})
                        head_left, head_mid, head_right = st.columns([3, 2, 1])
                        head_left.markdown(f"**{pkg_candidate.get('brand_name', '')} {pkg_candidate.get('model_name', package.get('external_label', 'Heater package'))}**")
                        head_left.caption(f"SKU: {pkg_candidate.get('sku', 'Unknown')} | Units: {pkg_candidate.get('unit_count', 1)} | Attached by: {package.get('attached_by') or 'operator'}")
                        head_mid.write(f"**Profile:** {pkg_summary.get('package_profile', 'auto')} / {pkg_summary.get('labor_profile', 'standard')}")
                        head_mid.write(f"**Totals:** Equipment {pkg_summary.get('equipment_total', 0):,.2f} | Labor {pkg_summary.get('labor_total', 0):,.2f} | Materials {pkg_summary.get('materials_total', 0):,.2f}")
                        if head_right.button('Remove package', key=f"remove_heater_package_{case['id']}_{package['external_link_id']}", help='Remove this attached equipment package from the quote case. This does not delete the saved heater sizing run itself.'):
                            with Session(engine) as session:
                                try:
                                    remove_heater_package_from_quote_case(session, quote_case_id=case['id'], external_link_id=package['external_link_id'])
                                    st.success('Attached heater package removed.')
                                except ValueError as exc:
                                    st.error(str(exc))
                            st.rerun()
                        package_rows = [
                            {
                                'Name': line.get('name'),
                                'Description': line.get('description'),
                                'Qty': float(line.get('qty') or 0),
                                'Unit Price': float(line.get('amount') or 0),
                                'Line Total': (float(line.get('qty') or 0) * float(line.get('amount') or 0)),
                                'Category': line.get('category', ''),
                            }
                            for line in package.get('prepared_lines', [])
                        ]
                        if package.get('has_overrides'):
                            st.info('This package has edited line overrides. FreshBooks draft creation will use these edited lines first for this quote case.')
                        if package_rows:
                            edited_rows = st.data_editor(
                                pd.DataFrame(package_rows),
                                key=f"heater_package_editor_{case['id']}_{package['external_link_id']}",
                                width='stretch',
                                num_rows='dynamic',
                                hide_index=True,
                                disabled=['Line Total'],
                            )
                            editor_left, editor_right = st.columns([1, 1])
                            if editor_left.button('Save package line overrides', key=f"save_heater_package_{case['id']}_{package['external_link_id']}", help='Save edited package lines for this quote case. These edited lines will be used by FreshBooks draft creation before the original attached package lines.'):
                                edited_payload = []
                                for _, row in edited_rows.iterrows():
                                    name = str(row.get('Name') or '').strip()
                                    if not name:
                                        continue
                                    try:
                                        qty = float(row.get('Qty') or 0)
                                    except (TypeError, ValueError):
                                        qty = 0.0
                                    try:
                                        amount = float(row.get('Unit Price') or 0)
                                    except (TypeError, ValueError):
                                        amount = 0.0
                                    edited_payload.append(
                                        {
                                            'name': name,
                                            'description': str(row.get('Description') or '').strip(),
                                            'qty': qty,
                                            'amount': amount,
                                            'category': str(row.get('Category') or 'misc_materials').strip() or 'misc_materials',
                                            'code': package.get('package_summary', {}).get('currency_code', 'USD'),
                                        }
                                    )
                                with Session(engine) as session:
                                    try:
                                        update_heater_package_lines(
                                            session,
                                            quote_case_id=case['id'],
                                            external_link_id=package['external_link_id'],
                                            edited_lines=edited_payload,
                                            edited_by='streamlit_operator',
                                        )
                                        st.success('Package line overrides saved.')
                                    except ValueError as exc:
                                        st.error(str(exc))
                                st.rerun()
                            if editor_right.button('Reset package lines', key=f"reset_heater_package_{case['id']}_{package['external_link_id']}", help='Restore the original attached package lines and clear any quote-case-specific edits for this package.'):
                                with Session(engine) as session:
                                    try:
                                        reset_heater_package_lines(
                                            session,
                                            quote_case_id=case['id'],
                                            external_link_id=package['external_link_id'],
                                        )
                                        st.success('Package lines reset to the original attached values.')
                                    except ValueError as exc:
                                        st.error(str(exc))
                                st.rerun()
                        st.divider()

            move_cols = st.columns([3, 2, 1])
            target_stage_slug = move_cols[0].selectbox(
                f"Move {case['quote_number']} to",
                options=[item['slug'] for item in stage_choices],
                index=[item['slug'] for item in stage_choices].index(case['stage_slug']),
                format_func=lambda slug, labels=allowed_stage_labels: labels[slug],
                key=f"move_target_{case['id']}",
                help='Select the next stage you want the case to move into. Allowed stage rules are enforced by the service layer.',
            )
            move_reason = move_cols[1].text_input(
                'Move note',
                key=f"move_reason_{case['id']}",
                help='Optional note explaining why the case is moving stages.',
            )
            if move_cols[2].button('Move', key=f"move_button_{case['id']}", help='Apply the stage change for this quote case.'):
                with Session(engine) as session:
                    move_quote_case(
                        session,
                        case['id'],
                        target_stage_slug=target_stage_slug,
                        moved_by='streamlit_operator',
                        move_reason=move_reason,
                    )
                st.rerun()

            with st.expander(f"CRM sync controls for {case['quote_number']}", expanded=False):
                contact_default = lacrm_links['contact_link']['external_id'] if lacrm_links['contact_link'] else ''
                contact_name_default = lacrm_links['contact_link']['external_label'] if lacrm_links['contact_link'] else ''
                sync_a, sync_b, sync_c = st.columns([2, 2, 1])
                lacrm_contact_id = sync_a.text_input(
                    'LACRM contact id',
                    value=contact_default,
                    key=f"lacrm_contact_id_{case['id']}",
                    help='Paste the matching LACRM ContactId or CompanyId so this quote knows which CRM record to sync.',
                )
                lacrm_contact_name = sync_b.text_input(
                    'LACRM contact label',
                    value=contact_name_default,
                    key=f"lacrm_contact_name_{case['id']}",
                    help='Optional human-friendly label to make the stored CRM link easier to recognize later.',
                )
                if sync_c.button('Save contact link', key=f"save_contact_link_{case['id']}", help='Store the LACRM contact id on this quote case without sending any live CRM write.'):
                    if not lacrm_contact_id.strip():
                        st.error('A contact id is required to save the CRM link.')
                    else:
                        with Session(engine) as session:
                            link_quote_case_to_lacrm_contact(
                                session,
                                case['id'],
                                contact_id=lacrm_contact_id.strip(),
                                contact_name=lacrm_contact_name.strip(),
                            )
                        st.success('LACRM contact link saved.')
                        st.rerun()

                sync_note = st.text_area(
                    'Sync note',
                    value=f"Quote case {case['quote_number']} synced from dashboard.",
                    key=f"sync_note_{case['id']}",
                    help='This note is sent to LACRM with the pipeline item update or create action so staff can see where the change came from.',
                )
                sync_live = st.checkbox(
                    'Force live sync for this one action',
                    value=False,
                    key=f"force_live_{case['id']}",
                    help='Only turn this on after the mapping is correct and the API key is configured. Leave it off to safely store a dry run.',
                )
                if st.button('Prepare or run LACRM sync', key=f"run_lacrm_sync_{case['id']}", help='Create or update the matching LACRM pipeline item. In dry run mode this only saves the intended operations locally.'):
                    with Session(engine) as session:
                        result = sync_quote_case_to_lacrm(
                            session,
                            case['id'],
                            note=sync_note.strip(),
                            force_live=sync_live,
                            create_follow_up_task=True,
                        )
                    if result['sync_status'] in {'synced', 'dry_run_ready'}:
                        st.success(result['message'])
                    else:
                        st.warning(result['message'])
                    st.rerun()


            with st.expander(f"FreshBooks draft controls for {case['quote_number']}", expanded=False):
                fb_client_default = freshbooks_links['client_link']['external_id'] if freshbooks_links['client_link'] else ''
                fb_client_name_default = freshbooks_links['client_link']['external_label'] if freshbooks_links['client_link'] else ''
                fb_link_a, fb_link_b, fb_link_c = st.columns([2, 2, 1])
                freshbooks_client_id = fb_link_a.text_input(
                    'FreshBooks client id',
                    value=fb_client_default,
                    key=f"freshbooks_client_id_{case['id']}",
                    help='Optional manual client id link when you already know the matching FreshBooks client record.',
                )
                freshbooks_client_name = fb_link_b.text_input(
                    'FreshBooks client label',
                    value=fb_client_name_default,
                    key=f"freshbooks_client_name_{case['id']}",
                    help='Optional human-friendly client label to make the stored link easier to recognize later.',
                )
                if fb_link_c.button('Save FB client link', key=f"save_fb_client_link_{case['id']}", help='Store the matching FreshBooks client id locally without creating or updating a draft yet.'):
                    if not freshbooks_client_id.strip():
                        st.error('A FreshBooks client id is required to save the client link.')
                    else:
                        with Session(engine) as session:
                            link_quote_case_to_freshbooks_client(
                                session,
                                case['id'],
                                client_id=freshbooks_client_id.strip(),
                                client_name=freshbooks_client_name.strip(),
                            )
                        st.success('FreshBooks client link saved.')
                        st.rerun()

                fb_form_a, fb_form_b = st.columns(2)
                fb_organization = fb_form_a.text_input(
                    'Organization',
                    value=freshbooks_client_name or case['requester_name'],
                    key=f"fb_org_{case['id']}",
                    help='FreshBooks organization or company name that should appear on the draft estimate.',
                )
                fb_currency = fb_form_b.text_input(
                    'Currency code',
                    value='USD',
                    key=f"fb_currency_{case['id']}",
                    help='Three-letter currency code for the estimate draft, such as USD.',
                )
                fb_terms = st.text_area(
                    'Estimate terms',
                    value='',
                    key=f"fb_terms_{case['id']}",
                    help='Terms that should appear on the estimate, such as payment timing or job conditions.',
                )
                fb_notes = st.text_area(
                    'Estimate notes',
                    value=case['description'] or '',
                    key=f"fb_notes_{case['id']}",
                    help='Internal or customer-facing estimate note content for this draft.',
                )
                line_a, line_b, line_c, line_d = st.columns([2, 2, 1, 1])
                fb_line_name = line_a.text_input(
                    'Primary line item',
                    value=case['title'],
                    key=f"fb_line_name_{case['id']}",
                    help='Main estimate line name for the first draft version. Additional structured line support can be expanded later.',
                )
                fb_line_description = line_b.text_input(
                    'Line description',
                    value=case['description'] or '',
                    key=f"fb_line_description_{case['id']}",
                    help='Description for the first estimate line on the draft.',
                )
                fb_line_qty = line_c.number_input(
                    'Qty',
                    min_value=1.0,
                    value=1.0,
                    step=1.0,
                    key=f"fb_line_qty_{case['id']}",
                    help='Quantity for the first estimate line.',
                )
                fb_line_amount = line_d.number_input(
                    'Unit price',
                    min_value=0.0,
                    value=0.0,
                    step=1.0,
                    key=f"fb_line_amount_{case['id']}",
                    help='Unit price for the first estimate line. Keep this at zero if the quote still needs final costing.',
                )
                fb_sync_note = st.text_area(
                    'FreshBooks sync note',
                    value=f"Quote case {case['quote_number']} draft prepared from the dashboard.",
                    key=f"fb_sync_note_{case['id']}",
                    help='Internal note stored with the prepared or live FreshBooks draft operation.',
                )
                fb_live = st.checkbox(
                    'Force live FreshBooks draft action',
                    value=False,
                    key=f"fb_force_live_{case['id']}",
                    help='Turn this on only after OAuth access token and account id are configured. Leave it off to safely prepare the draft locally first.',
                )
                button_a, button_b, button_c = st.columns(3)
                if button_a.button('Prepare or Create Draft', key=f"fb_prepare_{case['id']}", help='Prepare a local FreshBooks draft package or create a live estimate draft when live mode is enabled and credentials are ready.'):
                    line_payload = [
                        {
                            'name': fb_line_name.strip() or case['title'],
                            'description': fb_line_description.strip(),
                            'qty': float(fb_line_qty),
                            'amount': float(fb_line_amount),
                            'code': fb_currency.strip() or 'USD',
                            'type': 0,
                        }
                    ]
                    with Session(engine) as session:
                        result = sync_quote_case_to_freshbooks(
                            session,
                            case['id'],
                            lines=line_payload,
                            note=fb_sync_note.strip(),
                            force_live=fb_live,
                            create_client_if_missing=True,
                            currency_code=fb_currency.strip() or 'USD',
                            terms=fb_terms.strip(),
                            notes=fb_notes.strip(),
                            organization=fb_organization.strip(),
                        )
                    if result['sync_status'] in {'draft_prepared', 'draft_created'}:
                        st.success(result['message'])
                    else:
                        st.warning(result['message'])
                    st.rerun()
                if button_b.button('Refresh FB Status', key=f"fb_refresh_{case['id']}", help='Pull the linked FreshBooks estimate state back into the quote workflow when OAuth is configured and a real estimate id exists.'):
                    with Session(engine) as session:
                        try:
                            result = refresh_quote_case_from_freshbooks(session, case['id'], force_live=True)
                            st.success(result['message'])
                        except ValueError as exc:
                            st.error(str(exc))
                    st.rerun()
                if button_c.button('Mark Sent + Follow Up', key=f"fb_mark_sent_{case['id']}", help='Use this when the estimate was sent from FreshBooks and you want the local workflow to move into the follow up bucket immediately.'):
                    with Session(engine) as session:
                        try:
                            mark_quote_case_freshbooks_sent(session, case['id'], move_to_follow_up=True)
                            st.success('FreshBooks estimate marked sent and local follow up move applied.')
                        except ValueError as exc:
                            st.error(str(exc))
                    st.rerun()
