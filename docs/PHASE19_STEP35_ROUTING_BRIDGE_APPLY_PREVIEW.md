# Phase 19 Step 35 — Routing Bridge Apply Preview

## Purpose

Step 35 adds a dry-run bridge apply preview for future routing preference drafts.

It shows what bridge routing payloads would look like if drafts were later approved for application, but it does not call the bridge and does not write anything.

## Files

```text
app/services/routing_bridge_apply_preview.py
app/api/routes/routing_bridge_apply_preview.py
app/api/app.py
scripts/phase19_generate_routing_bridge_apply_preview.ps1
ui/pages/37_Routing_Bridge_Apply_Preview.py
docs/PHASE19_STEP35_ROUTING_BRIDGE_APPLY_PREVIEW.md
tests/test_phase19_routing_bridge_apply_preview.py
```

## Safety

This step does not:

- patch the bridge
- call LACRM
- create routing preference drafts
- save routing rules
- call bridge POST endpoints
- mutate bridge state
- mutate platform records
- enable live writes

This step is preview-only. It does not save routing rules, does not mutate bridge state, does not call LACRM, and does not enable live writes.

## API endpoints

```text
GET /front-desk/routing/bridge-apply-preview/status
GET /front-desk/routing/bridge-apply-preview
```

The preview rows include target endpoint and payload shape, but no request is sent to the bridge.

## View

Open Streamlit:

```text
http://127.0.0.1:8501
```

Then open:

```text
Routing Bridge Apply Preview
```

## Commit guard

Stage only the Step 35 files. Do not stage generated preview reports, local databases, `.env`, `.venv`, bridge folders, backups, evidence packs, import artifacts, or unrelated Replaster Quote files.
