# Phase 19 Step 2 — Unified Platform Receiver for KPS Bridge Events

This patch prepares the unified platform to receive raw RingCentral events from the standalone KPS Bridge.

## What changed

- The existing `POST /connectors/ringcentral/events` endpoint remains the receiver.
- RingCentral normalization now accepts:
  - nested webhook-style SMS payloads (`body.message`)
  - direct bridge/Message Sync SMS records (`body.id`, `body.subject`, `body.from`, `body.to`)
  - telephony session payloads with `body.parties`
  - bridge-wrapped Message Sync records with `bridge_context`
- Raw, normalized, and materialized records now dedupe repeated pushes by external id, payload hash, normalized fingerprint, and SMS message external id.

## Why this is safe

This preserves the platform's raw → normalized → materialized pipeline. The bridge does not write directly into platform business tables; it only sends source events to the connector/staging endpoint.

## Local platform run

Example:

```powershell
cd C:\path\to\unified-platform
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
uvicorn app.api.main:app --host 127.0.0.1 --port 8010
```

## Receiver endpoint

```text
POST http://127.0.0.1:8010/connectors/ringcentral/events
```

Body:

```json
{
  "payload": {
    "event": "/restapi/v1.0/account/~/extension/~/message-store/instant?type=SMS",
    "body": {
      "id": "example",
      "type": "SMS",
      "direction": "Inbound",
      "subject": "Message text",
      "from": {"phoneNumber": "+13055550199"},
      "to": [{"phoneNumber": "+13055550000"}],
      "creationTime": "2026-04-19T13:30:00Z"
    }
  }
}
```

## Validation

Run:

```powershell
pytest -q
```

Expected after this patch:

```text
57 passed
```
