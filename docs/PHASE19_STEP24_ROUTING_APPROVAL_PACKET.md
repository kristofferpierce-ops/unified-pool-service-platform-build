# Phase 19 Step 24 — Routing Approval Packet

## Purpose

Step 24 turns the dry-run routing migration preview from Step 23 into an operator review packet.

The packet is meant for review and planning only. It does not create platform routing preferences and does not touch bridge routing rules.

## Files

```text
scripts/phase19_generate_routing_approval_packet.ps1
ui/pages/26_Routing_Approval_Packet.py
docs/PHASE19_STEP24_ROUTING_APPROVAL_PACKET.md
tests/test_phase19_routing_approval_packet.py
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

This step is packet-only. It does not save routing rules, does not mutate bridge state, does not call LACRM, and does not enable live writes.

## Generate a packet

From the platform repo:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\phase19_generate_routing_approval_packet.ps1
```

Output:

```text
C:\Users\krist\Desktop\unified_pool_service_platform_build\backups\phase19_routing_approval_packet_<timestamp>
```

The packet folder contains:

```text
phase19_routing_approval_packet.json
phase19_routing_approval_packet.csv
phase19_routing_approval_packet.md
```

## View

Open Streamlit:

```text
http://127.0.0.1:8501
```

Then open:

```text
Routing Approval Packet
```

## Commit guard

Stage only the four Step 24 files. Do not stage generated packets, local databases, `.env`, `.venv`, bridge folders, backups, evidence packs, or unrelated Replaster Quote files.
