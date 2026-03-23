# Quote workflow and dashboard rollout plan

## Objective

Build Repo B into the quote orchestration layer that keeps the CRM, internal pricing logic, and FreshBooks proposal flow aligned without forcing a full rebuild every time a workflow rule changes.

## Guiding rule

One internal `quote_case` should anchor the workflow.

External systems should attach to that case:

- Less Annoying CRM for pipeline visibility and movement
- FreshBooks for customer facing estimate drafts, sends, and view status
- Heritage for live product pricing and later heater quote recommendations

## Rollout blocks

### Block 0
Stabilize the current platform baseline.

Scope:
- fix the RingCentral SMS datetime bug
- keep tests green before adding more moving parts
- avoid any schema changes that break current estimators, invoice review, or front desk flows

### Block 1A
Quote workflow foundation and dashboard mirror.

Scope:
- add `quote_case` tables
- add stage history
- add external link tracking for CRM and FreshBooks records
- seed admin editable workflow config from the current CRM bucket language
- add quote workflow API routes
- update the Streamlit home screen into a dashboard shell
- add a dedicated quote workflow page for creating, reviewing, and moving cases

Done when:
- a quote case can be created
- a quote case can be moved between allowed stages
- the dashboard shows counts by pipeline and stage
- stale cases, follow ups due, and sent but not viewed indicators show up

### Block 1B
Less Annoying CRM synchronization.

Scope:
- map internal pipelines and stages to LACRM pipeline records
- push case creation from program side into LACRM
- push case stage movement from program side into LACRM
- ingest LACRM changes back into the platform through a reconcile job or webhook adapter
- expose sync health and conflict notes in the quote case detail view

Done when:
- moving a quote in the program can update LACRM
- a change in LACRM can be seen and reconciled in the program
- both systems can be checked for drift

### Block 1C
FreshBooks draft estimate flow.

Scope:
- build estimate draft payloads from internal quote lines
- create draft estimates automatically from approved cases
- keep sent, viewed, accepted, and invoiced status linked back to the quote case
- move cases to the follow up bucket when the estimate is sent

Done when:
- the program can create a draft estimate
- the estimate can stay in draft until reviewed
- send and viewed status can be reflected in the dashboard

### Block 1D
Follow up intelligence.

Scope:
- due today queue
- viewed but not followed up queue
- stale quote queue
- owner and workload dashboard slices
- configurable follow up timing per pipeline and stage

### Block 2A
Heater quote module.

Scope:
- heating requirement calculator
- candidate heater search through the Heritage adapter
- live price snapshots attached to the quote case
- selected heater pushed into estimate lines

Inputs should include:
- outdoor air temperature
- current water temperature
- target water temperature
- gallons or dimensions
- covered or uncovered
- desired heat up window
- preferred heater type

### Block 2B
Reusable equipment quote framework.

Scope:
- pump quote module
- filter quote module
- automation quote module
- salt system quote module
- heater and chiller expansions

## File map for Block 1A

New files:
- `app/models/quote_tables.py`
- `app/services/quote_workflow.py`
- `app/api/routes/quote_workflow.py`
- `ui/pages/11_Quote_Workflow.py`
- `tests/test_quote_workflow.py`

Updated files:
- `app/models/__init__.py`
- `app/api/app.py`
- `app/services/bootstrap.py`
- `app/services/ingestion.py`
- `ui/app.py`

## Change management rule

Workflow behavior should come from settings and mappings first, not hardcoded page logic.

These values should stay editable:
- pipeline names
- stage names
- allowed transitions
- stale thresholds
- follow up timing
- FreshBooks status behavior
- LACRM stage mappings

## Suggested branch order

```powershell
cd C:\Users\krist\Desktop\unified_pool_service_platform_build\unified_pool_service_platform_build

git switch platform-integration-block1-dashboard-shell
git switch -c platform-integration-block1a-quote-workflow-foundation
```

## Validation commands

```powershell
cd C:\Users\krist\Desktop\unified_pool_service_platform_build\unified_pool_service_platform_build

python -m pytest
python -m streamlit run ui\app.py
python -m uvicorn app.api.main:app --reload
```
