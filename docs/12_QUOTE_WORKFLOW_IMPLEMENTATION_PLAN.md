# Quote Workflow Implementation Plan

## Current block status

### Block 1A
Completed in the local repo before this patch bundle:
- quote case tables
- dashboard shell
- quote workflow page
- stage movement rules
- age and stale tracking
- initial dashboard metrics

### Block 1B
This patch bundle adds the LACRM synchronization layer in a safe default mode.

## Block 1B goals

- keep Repo B as the quote and workflow orchestration layer
- mirror the bucket system already used by staff in LACRM
- allow quote cases to store the matching LACRM contact id
- map internal pipeline and stage slugs to real LACRM pipeline and status ids
- prepare or run LACRM sync from the program side
- keep default behavior safe by using dry run mode until live mode is explicitly enabled
- receive LACRM webhook updates and reconcile them back into the quote case ledger

## Safe default behavior

This block keeps the compare first and review first philosophy.

Default behavior:
- local quote workflow still works without any CRM credentials
- sync mode defaults to `dry_run`
- a dry run stores the intended LACRM operations on the quote case links without sending a live CRM write
- live writes only happen when the user explicitly enables live mode and provides a valid `LACRM_API_KEY`

## New LACRM components

### Connector layer
- `app/connectors/lacrm/client.py`
- `app/connectors/lacrm/contracts.py`

Responsibilities:
- call the official LACRM API with API key authorization
- fetch pipelines and statuses
- create and edit pipeline items
- create and edit follow up tasks
- provide a connection status summary for the UI

### Service layer
- `app/services/lacrm_sync.py`

Responsibilities:
- create and maintain the local LACRM sync config
- refresh local pipeline and status ids from live LACRM names
- store LACRM contact links on quote cases
- prepare dry run sync operations
- optionally perform live LACRM pipeline item and task writes
- reconcile inbound LACRM pipeline status updates back into local quote stages
- store and verify the LACRM webhook secret

### Route layer
- `app/api/routes/quote_workflow.py`

New API surfaces:
- `GET /quote-workflow/lacrm/mapping`
- `POST /quote-workflow/lacrm/mapping/refresh`
- `GET /quote-workflow/cases/{id}/lacrm`
- `POST /quote-workflow/cases/{id}/lacrm/contact-link`
- `POST /quote-workflow/cases/{id}/lacrm/sync`
- `POST /quote-workflow/lacrm/reconcile`
- `POST /quote-workflow/lacrm/webhook`

### UI layer
- `ui/Dashboard.py`
- `ui/pages/11_Quote_Workflow.py`

New UI behavior:
- dashboard shows LACRM pending and drift counts
- dashboard shows mapping readiness
- quote workflow page shows contact link, pipeline item link, follow up task link, blockers, and per case sync controls
- every clickable action includes help text so staff can tell what it does before clicking

## LACRM mapping model

Local quote workflow config still owns the human workflow semantics.

Block 1B adds a second config layer for CRM alignment:
- internal pipeline slug
- internal pipeline name
- LACRM pipeline name
- LACRM pipeline id
- internal stage slug
- internal stage name
- LACRM stage name
- LACRM status id

This means staff can keep using familiar bucket names while the program learns the exact CRM ids.

## Sync states used by quote cases

The patch uses these practical states:
- `local_only`
- `pending_sync`
- `pending_contact_link`
- `pending_mapping`
- `dry_run_ready`
- `synced`
- `sync_failed`
- `drift`
- `external_deleted`

## Webhook behavior

The webhook endpoint supports the LACRM handshake flow:
- if `X-Hook-Secret` is present, the program stores it and echoes it back
- later webhook payloads are validated using `X-Hook-Signature`
- `PipelineItemStatus.Create` and `PipelineItemStatus.Update` can reconcile a pipeline item status change back into the local quote case
- `PipelineItemStatus.Delete` marks the linked case for manual review rather than silently removing anything

## Expected env vars

Optional for dry run only:
- none

Required for live refresh and live write actions:
- `LACRM_API_KEY`

Optional overrides:
- `LACRM_API_BASE_URL`

## Expected env vars for Block 1C

Optional for dry run only:
- none

Required for live FreshBooks draft creation and live status refresh:
- `FRESHBOOKS_ACCESS_TOKEN`
- `FRESHBOOKS_ACCOUNT_ID`

Optional overrides:
- `FRESHBOOKS_API_BASE_URL`
- `FRESHBOOKS_API_VERSION`

## Block 1C
FreshBooks estimate draft orchestration

Implemented objectives in this patch set:
- add a FreshBooks OAuth-based connector layer that can read identity context, create clients, create estimate drafts, update estimate drafts, and refresh estimate state
- keep FreshBooks client and estimate ids linked back to each quote case using the existing external link ledger
- prepare draft estimates safely in dry run mode before any live write happens
- support a manual "mark sent and move to follow up" bridge so staff can keep the quote pipeline aligned even before full send-by-email automation is turned on
- support webhook verification storage and signed webhook reconcile for estimate events
- surface FreshBooks readiness and draft status in the dashboard and quote workflow page

## What this block deliberately does not do yet

- it does not implement the full FreshBooks OAuth authorization code and token refresh loop yet
- it does not automate send-by-email directly from the UI yet
- it does not add structured multi-line estimate authoring tables beyond the first practical draft line in the UI
- it does not change estimator logic
- it does not move any replay logic out of Repo A

## Next planned block after 1C

### Block 2A
Heater quote module and vendor-backed equipment draft lines

Planned objectives:
- calculate heating demand from pool and temperature inputs
- pull matching heater options and live pricing from the Heritage adapter
- let staff push selected heater lines directly into the quote case and FreshBooks draft workflow
