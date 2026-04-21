# Phase 19 Step 36 — Bridge Routing Write Contract

## Purpose

Step 36 inspects the original bridge routing UI/source markers and records a read-only bridge routing write contract.

It does not call the bridge write endpoint. It only documents the likely endpoint, payload shape, required future safety gates, and rollback requirements.

## Files

```text
scripts/phase19_generate_bridge_routing_write_contract.ps1
ui/pages/38_Bridge_Routing_Write_Contract.py
docs/PHASE19_STEP36_BRIDGE_ROUTING_WRITE_CONTRACT.md
tests/test_phase19_bridge_routing_write_contract.py
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

This step is contract-only. It does not save routing rules, does not mutate bridge state, does not call LACRM, and does not enable live writes.

## Generate contract report

From the platform repo:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\phase19_generate_bridge_routing_write_contract.ps1
```

Output:

```text
C:\Users\krist\Desktop\unified_pool_service_platform_build\backups\phase19_bridge_routing_write_contract_<timestamp>
```

The report folder contains:

```text
phase19_bridge_routing_write_contract.json
phase19_bridge_routing_write_contract.md
phase19_bridge_routing_write_contract_source_matches.csv
```

## View

Open Streamlit:

```text
http://127.0.0.1:8501
```

Then open:

```text
Bridge Routing Write Contract
```

## Commit guard

Stage only the four Step 36 files. Do not stage generated contract reports, local databases, `.env`, `.venv`, bridge folders, backups, evidence packs, import artifacts, or unrelated Replaster Quote files.
