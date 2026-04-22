# Phase 20 Step 4 — Bridge Routing HTTP Client Preflight Matrix

## Purpose

Phase 20 Step 4 builds a no-network preflight matrix for the bridge routing HTTP client path.

It reads the Phase 20 Step 3 dry-run validation report, Phase 20 Step 2 dry-run transport report, optional Phase 20 Step 1 stub report, optional Phase 19 Step 50 release checkpoint, and current runtime statuses.

## Files

```text
scripts/phase20_generate_bridge_routing_http_client_preflight_matrix.ps1
ui/pages/56_Bridge_Routing_HTTP_Client_Preflight_Matrix.py
docs/PHASE20_STEP4_BRIDGE_ROUTING_HTTP_CLIENT_PREFLIGHT_MATRIX.md
tests/test_phase20_bridge_routing_http_client_preflight_matrix.py
```

## Safety

This step does not:

- patch the bridge
- call LACRM
- save routing rules
- call bridge POST endpoints
- mutate bridge state
- mutate platform records
- create audit rows
- create rollback rows
- add a real bridge HTTP client
- add network transport
- add a live bridge write execution endpoint
- enable live writes

This step is HTTP-client-preflight-matrix-only and bridge GET only. It does not write to the bridge, does not mutate bridge state, does not call LACRM, and does not enable live writes.

## Generate preflight matrix

From the platform repo, with FastAPI and bridge running:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\phase20_generate_bridge_routing_http_client_preflight_matrix.ps1
```

Output:

```text
C:\Users\krist\Desktop\unified_pool_service_platform_build\backups\phase20_bridge_routing_http_client_preflight_matrix_<timestamp>
```

The folder contains:

```text
phase20_bridge_routing_http_client_preflight_matrix.json
phase20_bridge_routing_http_client_preflight_matrix_global_gates.csv
phase20_bridge_routing_http_client_preflight_matrix_rows.csv
phase20_bridge_routing_http_client_preflight_matrix_issues.csv
phase20_bridge_routing_http_client_preflight_matrix.md
```

## View

Open Streamlit:

```text
http://127.0.0.1:8501
```

Then open:

```text
Bridge Routing HTTP Client Preflight Matrix
```

## Commit guard

Stage only the four Phase 20 Step 4 files. Do not stage generated preflight matrix reports, local databases, `.env`, `.venv`, bridge folders, backups, evidence packs, import artifacts, or unrelated Replaster Quote files.
