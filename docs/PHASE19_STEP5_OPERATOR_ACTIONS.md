# Phase 19 Step 5 — Platform Operator Actions

Step 5 turns the read-only bridge-origin SMS review view into a controlled platform-side review workspace.

## Scope

This step is platform-only. It does not modify the live KPS Bridge, RingCentral subscriptions, or LACRM.

## Added capabilities

- Load/build candidate matches for a platform SMS thread.
- Approve a platform SMS thread to a chosen contact reference.
- Queue a platform follow-up task linked to the SMS thread.
- Save a platform routing preference for the external phone number.
- Show review-action summary counts for decisions, task links, routing preferences, and queued CRM apply actions.
- Display operator decisions, task links, and routing preferences on SMS thread detail.

## Safety boundary

The actions in this step write only to the platform database:

- `OperatorDecision`
- `CommunicationTaskLink`
- `CRMApplyAction` with `status='queued'`
- `RoutingPreference`
- SMS thread status/auto-attached flag

No LACRM note/task is created yet. The queued CRM apply action is intentionally local until a later bridge/LACRM apply step is implemented.

## New endpoint

```text
GET /front-desk/review-action-summary
```

Existing Step 4 endpoints remain available:

```text
GET /front-desk/sms-threads
GET /front-desk/sms-threads/{sms_thread_id}
GET /front-desk/bridge-review-summary
GET /front-desk/bridge-compare/sms-batches
```

Existing operator-action endpoints are now exposed in the UI:

```text
POST /front-desk/sms-threads/{sms_thread_id}/candidates
POST /front-desk/sms-threads/{sms_thread_id}/approve
POST /front-desk/sms-threads/{sms_thread_id}/task
POST /front-desk/routing-preferences
```

## Next step

Step 6 should connect selected platform decisions to a guarded LACRM apply workflow with dry-run, audit log, idempotency, and explicit operator confirmation.
