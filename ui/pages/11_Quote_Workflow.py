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
from app.services.heater_quote import apply_equipment_package_template_to_quote_case, build_equipment_package_template_from_builder_preview, build_equipment_package_template_from_wizard_preview, create_equipment_package_template_from_builder, create_equipment_package_template_from_wizard, create_manual_equipment_package_template, delete_equipment_package_template, get_equipment_family_builder_catalog, get_equipment_family_builder_wizard_catalog, get_equipment_package_template_summary, get_quote_case_equipment_package_workspace, list_equipment_package_templates, remove_heater_package_from_quote_case, reset_heater_package_lines, save_heater_package_template, update_heater_package_lines
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
    equipment_template_summary = get_equipment_package_template_summary(session)
    equipment_package_templates = list_equipment_package_templates(session)
    equipment_family_builder_catalog = get_equipment_family_builder_catalog(session)

pipeline_options = workflow_config.get('pipelines', [])
pipeline_lookup = {item['slug']: item for item in pipeline_options}

st.title('Quote Workflow')
st.caption('Create quote cases, move them across the mirrored CRM buckets, link them to the correct CRM contact, and prepare or run CRM sync from one place.')
st.info(f"Reusable equipment package templates available: {equipment_template_summary['template_count']}", icon='🧰')

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
                equipment_package_workspace = get_quote_case_equipment_package_workspace(session, case['id'])

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
                equipment_package_workspace['package_count'],
                help='How many equipment packages are currently attached to this quote case.',
            )
            package_metric_b.metric(
                'Package Total',
                f"{equipment_package_workspace['grand_total']:,.2f} {equipment_package_workspace['currency_code']}",
                help='Total of all attached equipment, material, allowance, and labor package lines currently linked to this quote case.',
            )



            with st.expander(f"Attached equipment packages for {case['quote_number']}", expanded=False):

                with st.expander('Create equipment package from wizard', expanded=False):
                    wizard_catalog = get_equipment_family_builder_wizard_catalog(session)
                    wizard_families = wizard_catalog.get('families', {}) if isinstance(wizard_catalog, dict) else {}
                    wizard_family_options = list(wizard_families.keys()) or ['pump', 'filter', 'salt_system', 'automation']
                    wizard_family_col, wizard_name_col = st.columns([1, 2])
                    wizard_family = wizard_family_col.selectbox(
                        'Wizard family',
                        options=wizard_family_options,
                        key=f'wizard_family_{case["id"]}',
                        format_func=lambda slug, families=wizard_families: families.get(slug, {}).get('label', slug.replace('_', ' ').title()),
                        help='Choose a structured equipment family wizard that will build package defaults from family-specific inputs.',
                    )
                    selected_wizard_family = wizard_families.get(wizard_family, {}) if isinstance(wizard_families.get(wizard_family), dict) else {}
                    wizard_template_name = wizard_name_col.text_input(
                        'Wizard template name',
                        value=str(selected_wizard_family.get('default_template_name') or f'{wizard_family.replace('_', ' ').title()} package template'),
                        key=f'wizard_template_name_{case["id"]}',
                        help='Reusable template name generated from the wizard inputs.',
                    )
                    wizard_fields = selected_wizard_family.get('fields', []) if isinstance(selected_wizard_family.get('fields'), list) else []
                    wizard_values = {}
                    if wizard_fields:
                        field_columns = st.columns(2)
                        for index, field in enumerate(wizard_fields):
                            if not isinstance(field, dict):
                                continue
                            name = str(field.get('name') or '').strip()
                            if not name:
                                continue
                            label = str(field.get('label') or name.replace('_', ' ').title())
                            field_type = str(field.get('type') or 'text')
                            key = f'wizard_input_{case["id"]}_{wizard_family}_{name}'
                            column = field_columns[index % 2]
                            if field_type == 'bool':
                                wizard_values[name] = column.checkbox(label, value=bool(field.get('default', False)), key=key)
                            elif field_type == 'enum':
                                options = list(field.get('options') or [])
                                default_value = field.get('default') if field.get('default') in options else (options[0] if options else '')
                                wizard_values[name] = column.selectbox(label, options=options, index=options.index(default_value) if default_value in options else 0, key=key) if options else ''
                            elif field_type == 'int':
                                wizard_values[name] = int(column.number_input(label, min_value=int(field.get('minimum', 0)), value=int(field.get('default', 0)), step=int(field.get('step', 1)), key=key))
                            elif field_type == 'float':
                                wizard_values[name] = float(column.number_input(label, min_value=float(field.get('minimum', 0.0)), value=float(field.get('default', 0.0)), step=float(field.get('step', 1.0)), key=key))
                            else:
                                wizard_values[name] = column.text_input(label, value=str(field.get('default', '')), key=key)
                    wizard_price_col, wizard_qty_col, wizard_labor_col = st.columns([1, 1, 1])
                    wizard_unit_price = wizard_price_col.number_input(
                        'Wizard equipment unit price',
                        min_value=0.0,
                        value=0.0,
                        step=50.0,
                        key=f'wizard_equipment_price_{case["id"]}',
                        help='Per-unit equipment allowance used for the package generated by the wizard.',
                    )
                    wizard_quantity = wizard_qty_col.number_input(
                        'Wizard quantity',
                        min_value=1,
                        max_value=24,
                        value=1,
                        step=1,
                        key=f'wizard_quantity_{case["id"]}',
                        help='How many complete equipment units the wizard should include in the package.',
                    )
                    wizard_labor_profiles = equipment_family_builder_catalog.get('labor_profiles', {}) if isinstance(equipment_family_builder_catalog, dict) else {}
                    wizard_labor_options = list(wizard_labor_profiles.keys()) or ['standard']
                    wizard_labor_profile = wizard_labor_col.selectbox(
                        'Wizard labor profile',
                        options=wizard_labor_options,
                        key=f'wizard_labor_profile_{case["id"]}',
                        format_func=lambda slug, labor=wizard_labor_profiles: labor.get(slug, {}).get('label', slug.replace('_', ' ').title()),
                        help='Labor profile applied to the package generated by the wizard.',
                    )
                    wizard_note = st.text_input(
                        'Wizard note',
                        key=f'wizard_note_{case["id"]}',
                        help='Optional internal note stored with the wizard-created reusable package template.',
                    )
                    wizard_misc_materials = st.number_input(
                        'Wizard miscellaneous materials allowance',
                        min_value=0.0,
                        value=0.0,
                        step=25.0,
                        key=f'wizard_misc_materials_{case["id"]}',
                        help='Optional extra materials allowance added to the generated package.',
                    )
                    wizard_preview_col, wizard_save_col = st.columns([1, 1])
                    if wizard_preview_col.button('Preview wizard package', key=f'preview_wizard_package_{case["id"]}', help='Preview the package lines this structured wizard will build before saving the reusable template.'):
                        with Session(engine) as session:
                            try:
                                wizard_preview = build_equipment_package_template_from_wizard_preview(
                                    session,
                                    package_kind=wizard_family,
                                    wizard_inputs=wizard_values,
                                    equipment_unit_price=wizard_unit_price,
                                    quantity=int(wizard_quantity),
                                    saved_by='streamlit_operator',
                                    template_name=wizard_template_name,
                                    template_description=wizard_note,
                                    labor_profile=wizard_labor_profile,
                                    misc_materials_amount=wizard_misc_materials,
                                )
                            except ValueError as exc:
                                st.error(str(exc))
                            else:
                                preview_rows = pd.DataFrame([
                                    {
                                        'Name': line.get('name'),
                                        'Description': line.get('description'),
                                        'Qty': line.get('qty'),
                                        'Unit Price': line.get('amount'),
                                        'Category': line.get('category'),
                                    }
                                    for line in wizard_preview['prepared_lines']
                                ])
                                st.write('Wizard preview')
                                st.dataframe(preview_rows, width='stretch')
                                preview_summary = wizard_preview.get('package_summary', {})
                                st.caption(f"Wizard profile: {wizard_preview.get('resolved_builder_profile', '')} · Preview total: {preview_summary.get('package_total', 0):,.2f} {preview_summary.get('currency_code', 'USD')}")
                    if wizard_save_col.button('Save wizard package template', key=f'save_wizard_package_template_{case["id"]}', help='Create a reusable equipment package template from the structured family wizard inputs.'):
                        with Session(engine) as session:
                            try:
                                create_equipment_package_template_from_wizard(
                                    session,
                                    template_name=wizard_template_name or f'{wizard_family.title()} wizard template',
                                    package_kind=wizard_family,
                                    wizard_inputs=wizard_values,
                                    equipment_unit_price=wizard_unit_price,
                                    quantity=int(wizard_quantity),
                                    saved_by='streamlit_operator',
                                    template_description=wizard_note,
                                    labor_profile=wizard_labor_profile,
                                    misc_materials_amount=wizard_misc_materials,
                                )
                                st.success('Wizard equipment package template saved.')
                            except ValueError as exc:
                                st.error(str(exc))
                        st.rerun()

                with st.expander('Create builder equipment package template', expanded=False):
                    builder_families = equipment_family_builder_catalog.get('families', {}) if isinstance(equipment_family_builder_catalog, dict) else {}
                    builder_labor_profiles = equipment_family_builder_catalog.get('labor_profiles', {}) if isinstance(equipment_family_builder_catalog, dict) else {}
                    builder_family_options = list(builder_families.keys()) or ['pump', 'filter', 'salt_system', 'automation']
                    builder_family_col, builder_profile_col = st.columns([1, 2])
                    builder_family = builder_family_col.selectbox(
                        'Builder family',
                        options=builder_family_options,
                        key=f'builder_family_{case["id"]}',
                        format_func=lambda slug, families=builder_families: families.get(slug, {}).get('label', slug.replace('_', ' ').title()),
                        help='Choose the equipment family to build from a structured starter profile.',
                    )
                    selected_family = builder_families.get(builder_family, {})
                    family_profiles = selected_family.get('profiles', {}) if isinstance(selected_family.get('profiles'), dict) else {}
                    builder_profile_options = list(family_profiles.keys())
                    default_profile = selected_family.get('default_profile') if isinstance(selected_family, dict) else None
                    default_index = builder_profile_options.index(default_profile) if default_profile in builder_profile_options else 0
                    builder_profile = builder_profile_col.selectbox(
                        'Builder profile',
                        options=builder_profile_options,
                        index=default_index if builder_profile_options else 0,
                        key=f'builder_profile_{case["id"]}',
                        format_func=lambda slug, profiles=family_profiles: profiles.get(slug, {}).get('label', slug.replace('_', ' ').title()),
                        help='Pick the family-specific starter package profile to build from.',
                    )
                    selected_profile = family_profiles.get(builder_profile, {}) if builder_profile else {}
                    option_labels = selected_profile.get('option_labels', {}) if isinstance(selected_profile.get('option_labels'), dict) else {}
                    builder_name_col, builder_equipment_col = st.columns([2, 2])
                    builder_template_name = builder_name_col.text_input(
                        'Builder template name',
                        value=f"{selected_family.get('label', builder_family.replace('_', ' ').title())} template",
                        key=f'builder_template_name_{case["id"]}',
                        help='Reusable template name created from the family builder.',
                    )
                    builder_equipment_name = builder_equipment_col.text_input(
                        'Equipment label',
                        value=selected_profile.get('default_equipment_name', ''),
                        key=f'builder_equipment_name_{case["id"]}',
                        help='Customer-facing equipment label used on the created package template.',
                    )
                    builder_price_col, builder_qty_col, builder_labor_col = st.columns([1, 1, 1])
                    builder_unit_price = builder_price_col.number_input(
                        'Equipment unit price',
                        min_value=0.0,
                        value=0.0,
                        step=50.0,
                        key=f'builder_equipment_price_{case["id"]}',
                        help='Per-unit equipment allowance that becomes the equipment line in the package.',
                    )
                    builder_quantity = builder_qty_col.number_input(
                        'Quantity',
                        min_value=1,
                        max_value=24,
                        value=1,
                        step=1,
                        key=f'builder_quantity_{case["id"]}',
                        help='How many units of this equipment family should be included in the built template.',
                    )
                    labor_profile_options = list(builder_labor_profiles.keys()) or ['standard']
                    builder_labor_profile = builder_labor_col.selectbox(
                        'Labor profile',
                        options=labor_profile_options,
                        key=f'builder_labor_profile_{case["id"]}',
                        format_func=lambda slug, labor=builder_labor_profiles: labor.get(slug, {}).get('label', slug.replace('_', ' ').title()),
                        help='Choose the labor profile used when building the package template.',
                    )
                    builder_note = st.text_input(
                        'Builder note',
                        key=f'builder_note_{case["id"]}',
                        help='Optional internal note stored with the reusable package template.',
                    )
                    builder_misc_materials = st.number_input(
                        'Miscellaneous materials allowance',
                        min_value=0.0,
                        value=0.0,
                        step=25.0,
                        key=f'builder_misc_materials_{case["id"]}',
                        help='Optional additional materials allowance added as its own package line.',
                    )
                    builder_option_values = {}
                    if option_labels:
                        st.caption('Builder options')
                        option_columns = st.columns(2)
                        for index, (option_name, option_label) in enumerate(option_labels.items()):
                            default_value = bool((selected_profile.get('default_options') or {}).get(option_name, False))
                            builder_option_values[option_name] = option_columns[index % 2].checkbox(
                                option_label,
                                value=default_value,
                                key=f'builder_option_{case["id"]}_{builder_family}_{builder_profile}_{option_name}',
                            )
                    preview_payload = None
                    preview_left, preview_right = st.columns([1, 1])
                    if preview_left.button('Preview builder package', key=f'preview_builder_package_{case["id"]}', help='Preview the package lines this family builder will create before saving a reusable template.'): 
                        with Session(engine) as session:
                            try:
                                preview_payload = build_equipment_package_template_from_builder_preview(
                                    session,
                                    template_name=builder_template_name,
                                    package_kind=builder_family,
                                    builder_profile=builder_profile,
                                    equipment_name=builder_equipment_name,
                                    equipment_unit_price=builder_unit_price,
                                    quantity=int(builder_quantity),
                                    saved_by='streamlit_operator',
                                    template_description=builder_note,
                                    labor_profile=builder_labor_profile,
                                    misc_materials_amount=builder_misc_materials,
                                    **builder_option_values,
                                )
                            except ValueError as exc:
                                st.error(str(exc))
                        if preview_payload:
                            st.write('Builder preview')
                            preview_rows = pd.DataFrame([
                                {
                                    'Name': line.get('name'),
                                    'Description': line.get('description'),
                                    'Qty': line.get('qty'),
                                    'Unit Price': line.get('amount'),
                                    'Category': line.get('category'),
                                }
                                for line in preview_payload['prepared_lines']
                            ])
                            st.dataframe(preview_rows, width='stretch')
                            preview_summary = preview_payload.get('package_summary', {})
                            st.caption(f"Preview total: {preview_summary.get('package_total', 0):,.2f} {preview_summary.get('currency_code', 'USD')}")
                    if preview_right.button('Save builder package template', key=f'save_builder_package_template_{case["id"]}', help='Create a reusable package template from the selected equipment family builder.'): 
                        with Session(engine) as session:
                            try:
                                create_equipment_package_template_from_builder(
                                    session,
                                    template_name=builder_template_name or f'{builder_family.title()} package template',
                                    package_kind=builder_family,
                                    builder_profile=builder_profile,
                                    equipment_name=builder_equipment_name,
                                    equipment_unit_price=builder_unit_price,
                                    quantity=int(builder_quantity),
                                    saved_by='streamlit_operator',
                                    template_description=builder_note,
                                    labor_profile=builder_labor_profile,
                                    misc_materials_amount=builder_misc_materials,
                                    **builder_option_values,
                                )
                                st.success('Builder equipment package template saved.')
                            except ValueError as exc:
                                st.error(str(exc))
                        st.rerun()

                with st.expander('Create manual equipment package template', expanded=False):
                    manual_kind_col, manual_name_col = st.columns([1, 2])
                    manual_kind = manual_kind_col.selectbox(
                        'Package family',
                        options=['pump', 'filter', 'salt_system', 'automation', 'other'],
                        key=f'manual_package_kind_{case["id"]}',
                        help='Select the equipment family for this reusable template.',
                    )
                    manual_template_name = manual_name_col.text_input(
                        'Manual template name',
                        key=f'manual_package_name_{case["id"]}',
                        help='Friendly name shown later when applying this reusable equipment template.',
                    )
                    manual_template_description = st.text_input(
                        'Template note',
                        key=f'manual_package_note_{case["id"]}',
                        help='Optional internal note about what this package is meant to cover.',
                    )
                    manual_default_rows = pd.DataFrame([
                        {'Name': f'{manual_kind.title()} equipment', 'Description': '', 'Qty': 1.0, 'Unit Price': 0.0, 'Category': 'equipment'},
                        {'Name': 'Installation labor', 'Description': '', 'Qty': 1.0, 'Unit Price': 0.0, 'Category': 'labor'},
                    ])
                    manual_rows = st.data_editor(
                        manual_default_rows,
                        key=f'manual_package_rows_{case["id"]}',
                        width='stretch',
                        num_rows='dynamic',
                        hide_index=True,
                    )
                    if st.button('Save manual equipment package template', key=f'save_manual_package_template_{case["id"]}', help='Save this manually entered package as a reusable equipment package template that can be applied to quote cases later.'):
                        lines_payload = []
                        for _, row in manual_rows.iterrows():
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
                            lines_payload.append({
                                'name': name,
                                'description': str(row.get('Description') or '').strip(),
                                'qty': qty,
                                'amount': amount,
                                'category': str(row.get('Category') or 'misc_materials').strip() or 'misc_materials',
                                'code': 'USD',
                            })
                        with Session(engine) as session:
                            try:
                                create_manual_equipment_package_template(
                                    session,
                                    template_name=manual_template_name or f'{manual_kind.title()} package template',
                                    package_kind=manual_kind,
                                    lines=lines_payload,
                                    saved_by='streamlit_operator',
                                    template_description=manual_template_description,
                                )
                                st.success('Manual equipment package template saved.')
                            except ValueError as exc:
                                st.error(str(exc))
                        st.rerun()

                template_left, template_mid, template_right = st.columns([3, 1, 1])
                if equipment_package_templates:
                    selected_template_slug = template_left.selectbox(
                        'Apply saved equipment package template',
                        options=[item['template_slug'] for item in equipment_package_templates],
                        format_func=lambda slug, items={item['template_slug']: item for item in equipment_package_templates}: f"[{items[slug].get('package_kind', 'equipment')}] {items[slug]['template_name']}",
                        key=f"apply_heater_template_{case['id']}",
                        help='Choose a saved heater package template to attach to this quote case.',
                    )
                    replace_existing_templates = template_mid.checkbox(
                        'Replace current packages in same family',
                        key=f"replace_template_attach_{case['id']}",
                        help='Remove currently attached packages in the same family before applying the selected template.',
                    )
                    if template_right.button('Apply template', key=f"apply_template_button_{case['id']}", help='Attach the selected saved equipment package template to this quote case.'):
                        with Session(engine) as session:
                            try:
                                apply_equipment_package_template_to_quote_case(
                                    session,
                                    template_slug=selected_template_slug,
                                    quote_case_id=case['id'],
                                    attached_by='streamlit_operator',
                                    replace_existing=replace_existing_templates,
                                )
                                st.success('Equipment package template applied.')
                            except ValueError as exc:
                                st.error(str(exc))
                        st.rerun()
                else:
                    st.caption('No saved equipment package templates exist yet. Save one from an attached package below to reuse it later.')

                if not equipment_package_workspace['packages']:
                    st.caption('No equipment packages are attached yet. Use the Heater Quote Tool for heater packages, or create and apply a saved equipment package template here.')
                else:
                    st.caption(f"Use the Heater Quote Tool with this quote case if you want to add or replace heater packages. Other package families can come from saved templates.")
                    for package in equipment_package_workspace['packages']:
                        pkg_candidate = package.get('candidate', {})
                        pkg_summary = package.get('package_summary', {})
                        head_left, head_mid, head_right = st.columns([3, 2, 1])
                        pkg_kind = package.get('package_kind', 'equipment')
                        package_title = (f"{pkg_candidate.get('brand_name', '')} {pkg_candidate.get('model_name', package.get('external_label', 'Equipment package'))}".strip() or package.get('external_label', 'Equipment package'))
                        head_left.markdown(f"**[{pkg_kind}] {package_title}**")
                        head_left.caption(f"SKU: {pkg_candidate.get('sku', 'n/a')} | Units: {pkg_candidate.get('unit_count', 1)} | Attached by: {package.get('attached_by') or 'operator'}")
                        head_mid.write(f"**Profile:** {pkg_summary.get('package_profile', 'auto')} / {pkg_summary.get('labor_profile', 'standard')}")
                        head_mid.write(f"**Totals:** Equipment {pkg_summary.get('equipment_total', 0):,.2f} | Labor {pkg_summary.get('labor_total', 0):,.2f} | Materials {pkg_summary.get('materials_total', 0):,.2f}")
                        template_name_value = st.text_input(
                            'Template name',
                            value=(f"{pkg_candidate.get('brand_name', '').strip()} {pkg_candidate.get('model_name', package.get('external_label', 'Equipment package')).strip()}".strip() or f"{pkg_kind.title()} package template"),
                            key=f"heater_template_name_{case['id']}_{package['external_link_id']}",
                            help='Name to save this attached equipment package as a reusable template for future quotes.',
                        )
                        action_left, action_right = st.columns([1, 1])
                        if action_left.button('Save as template', key=f"save_heater_template_{case['id']}_{package['external_link_id']}", help='Save this attached equipment package as a reusable template for future quote cases.'):
                            with Session(engine) as session:
                                try:
                                    save_heater_package_template(
                                        session,
                                        quote_case_id=case['id'],
                                        external_link_id=package['external_link_id'],
                                        template_name=template_name_value,
                                        saved_by='streamlit_operator',
                                    )
                                    st.success('Equipment package template saved.')
                                except ValueError as exc:
                                    st.error(str(exc))
                            st.rerun()
                        if action_right.button('Delete template match', key=f"delete_matching_template_{case['id']}_{package['external_link_id']}", help='Delete a saved template with this same name if it exists. This does not affect the attached package on the quote case.'):
                            matching = next((item for item in equipment_package_templates if item['template_name'] == template_name_value), None)
                            if not matching:
                                st.warning('No saved template with that name exists yet.')
                            else:
                                with Session(engine) as session:
                                    try:
                                        delete_equipment_package_template(session, matching['template_slug'])
                                        st.success('Saved equipment package template deleted.')
                                    except ValueError as exc:
                                        st.error(str(exc))
                                st.rerun()
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
