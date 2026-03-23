# Canonical domain and schema target

## Existing useful canonical domains from platform_v3
- expenses and overhead
- products and product price history
- climate and water profiles
- baseline model versions
- accounts, properties, and vessels
- estimate scenarios and estimate runs
- water tests, service logs, chemical usage logs
- calibration adjustments
- vendor orders and direct deliveries
- invoice documents and staged invoice lines
- tools and property verification cases

## Bridge runtime schema present today
From `bridge.db`:
- calls
- sms_batches
- sms_messages
- caller_relationships
- routing_rules
- processed_event_uuids
- message_sync_state

## Target new canonical domains
Add these internal tables or model groups:
- source_system
- connector_run
- raw_source_record
- normalized_source_record
- match_candidate
- approval_decision
- apply_event
- external_identity_map

Add communications domain:
- communication_event
- call_session
- voicemail_item
- sms_thread
- sms_message
- contact_match_candidate
- routing_preference
- operator_decision
- crm_apply_action
- communication_task_link

Add finance reconciliation domain:
- billing_document
- billing_line
- payment_event
- reconciliation_fact

Add operations domain:
- service_visit
- route_run
- technician_assignment
- field_observation
- actual_labor_fact
- actual_chemical_fact

Add intelligence domain:
- expectation_profile
- variance_fact
- driver_attribution_fact
- calibration_suggestion
- profitability_signal
- branch_overlay

## Rule
No external connector writes directly into trusted canonical tables.
Everything flows through the staged ingestion path first.
