# Phase 21 Step 6 - Phase 20 Network Transport Workspace Hygiene Packet

## Purpose

Phase 21 Step 6 continues the Phase 21 cleanup and consolidation phase.

It creates a no-write workspace hygiene packet for the Phase 20 bridge routing network transport design chain. It reads the latest Phase 21 Step 5 cleanup manifest packet and compares the current git status against the cleanup guidance so you can see current-step staging candidates, do-not-stage matches, and review-before-stage paths in one place.

## Files

```text
scripts/phase21_generate_phase20_network_transport_workspace_hygiene_packet.ps1
ui/pages/98_Phase20_Network_Transport_Workspace_Hygiene_Packet.py
docs/PHASE21_STEP6_PHASE20_NETWORK_TRANSPORT_WORKSPACE_HYGIENE_PACKET.md
tests/test_phase21_phase20_network_transport_workspace_hygiene_packet.py
```

## Safety

This step does not:

- patch the bridge
- call LACRM
- save routing rules
- call bridge POST endpoints
- call interface execution methods
- create design closure records
- record final approvals
- start an implementation phase
- create execution implementation
- add a real bridge HTTP client
- add network transport
- enable network transport
- arm network transport
- open network sockets
- create design-freeze records
- record operator signoffs
- create cutover packets
- record cutover approvals
- capture bridge responses
- create response capture records
- mutate bridge state
- mutate platform records
- record operator approvals
- create confirmation records
- set environment variables
- create audit rows
- create rollback rows
- create rollback snapshots
- add a bridge POST implementation
- add a live bridge write execution endpoint
- enable live writes

This step is Phase 20 network transport workspace-hygiene-only and a no-write workspace hygiene packet. It creates a git-status hygiene report but does not create design closure records, does not record final approvals, does not start an implementation phase, does not call interface execution methods, does not create execution implementation, does not add a real bridge HTTP client, does not add network transport, does not open network sockets, does not call bridge POST endpoints, does not mutate bridge or platform state, does not create audit or rollback rows, does not call LACRM, and does not enable live writes.

## Explicit no-write boundary phrases

This step does not create design closure records, does not record final approvals, does not start an implementation phase, does not create execution implementation, does not call interface execution methods, does not add a real bridge HTTP client, does not add network transport, does not open network sockets, does not call bridge POST endpoints, does not create design-freeze records, does not record operator signoffs, does not create cutover packets, does not capture bridge responses, does not create response capture records, does not set environment variables, does not create audit rows, does not mutate bridge state, does not mutate platform state, does not call LACRM, and does not enable live writes.

## Generate workspace hygiene packet

From the platform repo, with FastAPI and bridge running:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\phase21_generate_phase20_network_transport_workspace_hygiene_packet.ps1
```

Output:

```text
C:\Users\krist\Desktop\unified_pool_service_platform_build\backups\phase21_phase20_network_transport_workspace_hygiene_packet_<timestamp>
```

The folder contains:

```text
phase21_phase20_network_transport_workspace_hygiene_packet.json
phase21_phase20_network_transport_workspace_hygiene_packet_git_status.csv
phase21_phase20_network_transport_workspace_hygiene_packet_checklist.csv
phase21_phase20_network_transport_workspace_hygiene_packet_issues.csv
phase21_phase20_network_transport_workspace_hygiene_packet.md
```

## View

Open Streamlit:

```text
http://127.0.0.1:8501
```

Then open:

```text
Phase20 Network Transport Workspace Hygiene Packet
```

## Commit guard

Stage only the four Phase 21 Step 6 files. Do not stage generated workspace-hygiene files, local databases, `.env`, `.venv`, bridge folders, backups, evidence packs, import artifacts, or unrelated Replaster Quote files.
