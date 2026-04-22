# Phase 20 Step 10 — Bridge Routing Network Transport Preflight Matrix

## Purpose

Phase 20 Step 10 builds a no-socket preflight matrix for the bridge routing network transport path.

It reads the Phase 20 Step 9 dry-run adapter validation report, Phase 20 Step 8 dry-run adapter report, optional Phase 20 Step 7 guard report, optional Phase 20 Step 6 HTTP-client release checkpoint, and current runtime statuses.

## Files

```text
scripts/phase20_generate_bridge_routing_network_transport_preflight_matrix.ps1
ui/pages/62_Bridge_Routing_Network_Transport_Preflight_Matrix.py
docs/PHASE20_STEP10_BRIDGE_ROUTING_NETWORK_TRANSPORT_PREFLIGHT_MATRIX.md
tests/test_phase20_bridge_routing_network_transport_preflight_matrix.py
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
- enable network transport
- arm network transport
- open network sockets
- add a live bridge write execution endpoint
- enable live writes

This step is network-transport-preflight-matrix-only and bridge GET only. It does not write to the bridge, does not mutate bridge state, does not call LACRM, and does not enable live writes.

## Generate preflight matrix

From the platform repo, with FastAPI and bridge running:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\phase20_generate_bridge_routing_network_transport_preflight_matrix.ps1
```

Output:

```text
C:\Users\krist\Desktop\unified_pool_service_platform_build\backups\phase20_bridge_routing_network_transport_preflight_matrix_<timestamp>
```

The folder contains:

```text
phase20_bridge_routing_network_transport_preflight_matrix.json
phase20_bridge_routing_network_transport_preflight_matrix_global_gates.csv
phase20_bridge_routing_network_transport_preflight_matrix_rows.csv
phase20_bridge_routing_network_transport_preflight_matrix_issues.csv
phase20_bridge_routing_network_transport_preflight_matrix.md
```

## View

Open Streamlit:

```text
http://127.0.0.1:8501
```

Then open:

```text
Bridge Routing Network Transport Preflight Matrix
```

## Commit guard

Stage only the four Phase 20 Step 10 files. Do not stage generated preflight matrix reports, local databases, `.env`, `.venv`, bridge folders, backups, evidence packs, import artifacts, or unrelated Replaster Quote files.
