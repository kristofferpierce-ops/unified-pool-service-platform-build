# Phase 19 Step 10 — guarded live-apply readiness controls

Step 10 does **not** enable live LACRM writes. It adds another safety layer around the Step 6 dry-run apply path so a future live-write cutover cannot happen by accident.

## Added controls

Live LACRM writes remain blocked unless all of the following are true:

1. The request uses `dry_run=false`.
2. The request sets `confirm_live_write=true`.
3. `PLATFORM_LACRM_LIVE_WRITE_ENABLED=true` is configured.
4. `PLATFORM_LACRM_LIVE_WRITE_ARMED=true` is configured.
5. `LACRM_API_KEY` is configured.
6. At least one dry-run CRM apply action already exists.
7. There are no CRM apply actions in `error` status.
8. The operator submits the configured confirmation phrase.

The default phrase is:

```text
WRITE TO LACRM
```

It can be changed with:

```env
PLATFORM_LACRM_LIVE_WRITE_CONFIRMATION_PHRASE=WRITE TO LACRM
```

## New endpoint

```text
GET /front-desk/lacrm-apply/live-readiness
GET /front-desk/lacrm-apply/live-readiness?submitted_phrase=WRITE%20TO%20LACRM
```

This endpoint reports the live gate state without writing to LACRM.

## UI change

The Streamlit Bridge Review page now shows:

- Live Armed status
- Live Ready status
- Required confirmation phrase
- A typed confirmation phrase field for guarded apply attempts
- Step 10 live gate details in the Apply Audit tab

## Safety position

This step is intentionally conservative. Normal operators should keep `Dry run` enabled. Live apply should stay disabled until a separate operational cutover confirms credentials, idempotency, audit exports, and rollback procedures.
