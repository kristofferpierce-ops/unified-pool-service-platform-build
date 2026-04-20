# Phase 19 Step 23 — Routing Migration Preview

## Purpose

Step 23 creates a dry-run routing migration preview from the bridge routing rules snapshot created in Step 22.

It proposes how bridge routing rows could later become platform `RoutingPreference` candidates, but it does not write those candidates anywhere.

## Files

```text
scripts/phase19_generate_routing_migration_preview.ps1
ui/pages/25_Routing_Migration_Preview.py
docs/PHASE19_STEP23_ROUTING_MIGRATION_PREVIEW.md
tests/test_phase19_routing_migration_preview.py
```

## Safety

This step does not:

- patch the bridge
- call LACRM
- save routing rules
- call bridge POST endpoints
- mutate bridge state
- mutate platform records
- enable live writes

This step is preview-only. It does not save routing rules, does not mutate bridge state, does not call LACRM, and does not enable live writes.

## Generate a preview

From the platform repo:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\phase19_generate_routing_migration_preview.ps1
```

Output:

```text
C:\Users\krist\Desktop\unified_pool_service_platform_build\backups\phase19_routing_migration_preview_<timestamp>.json
C:\Users\krist\Desktop\unified_pool_service_platform_build\backups\phase19_routing_migration_preview_<timestamp>.md
```

## View

Open Streamlit:

```text
http://127.0.0.1:8501
```

Then open:

```text
Routing Migration Preview
```

## Commit guard

Stage only the four Step 23 files. Do not stage generated previews, local databases, `.env`, `.venv`, bridge folders, backups, evidence packs, or unrelated Replaster Quote files.
