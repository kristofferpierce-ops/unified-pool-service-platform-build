# Unified Pool Service Operations Core Build

This package is a **runnable foundation build** assembled from the uploaded seed packet, the legacy `pool_service_platform_v3` backbone, and the direct bridge app files.

It is not the fully finished production platform yet. It is the correct merged starting point for the next phase of implementation.

## What is in this build

### Active code foundation
- legacy `pool_service_platform_v3` code preserved and kept runnable
- new connector-first ingestion tables and services
- new communications domain for calls, voicemail, and SMS threads
- new front desk API layer
- persisted labor settings instead of hardcoded-only labor defaults
- simple front desk dashboard at `/`

### Reference material included in repo
- bridge direct source files in `legacy_bridge_reference/`
- extracted legacy repos and seed docs in `references/legacy_seed/` and `docs/`

## Implemented routes

### Core
- `GET /health`
- `POST /admin/bootstrap`
- `GET /`

### Settings
- `GET /system-settings/{key}`
- `PUT /system-settings/{key}`

### Estimating
- `POST /estimates/calculate`

### Connector intake
- `GET /connectors/sources`
- `POST /connectors/ringcentral/events`

### Front desk workflows
- `GET /front-desk/queue`
- `POST /front-desk/communications/{id}/candidates`
- `POST /front-desk/communications/{id}/approve`
- `POST /front-desk/communications/{id}/task`
- `POST /front-desk/sms-threads/{id}/candidates`
- `POST /front-desk/sms-threads/{id}/approve`
- `POST /front-desk/sms-threads/{id}/task`
- `POST /front-desk/routing-preferences`

### Legacy platform routes preserved
- expenses
- baseline models
- properties
- commercial
- invoices
- reports
- tools

## Run it

### 1. Create a virtual environment

```bash
python -m venv .venv
```

### 2. Activate it

Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

Mac/Linux:

```bash
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Initialize the database

```bash
python scripts/init_db.py
```

### 5. Run the API

```bash
uvicorn app.api.main:app --reload
```

Then open:
- `http://127.0.0.1:8000/` for the simple dashboard
- `http://127.0.0.1:8000/docs` for Swagger

## Example RingCentral event payload

```json
{
  "payload": {
    "event": "/restapi/v1.0/account/~/extension/~/message-store/instant?type=SMS",
    "body": {
      "event": "/restapi/v1.0/account/~/extension/~/message-store/instant?type=SMS",
      "message": {
        "id": "msg-1001",
        "direction": "Inbound",
        "subject": "Hi this is Mike at 123 Palm Ave. Heater is still down.",
        "from": {"phoneNumber": "+13055551212", "name": "Mike"},
        "to": [{"phoneNumber": "+13055550000"}],
        "creationTime": "2026-03-18T16:30:00+00:00"
      }
    }
  }
}
```

Post that to:

```text
POST /connectors/ringcentral/events
```

Then view the queue at:

```text
GET /front-desk/queue
```

## Important next steps

1. move to Postgres and Alembic
2. refactor invoice ingestion onto the new generic raw → normalized → matched → approved → applied pipeline
3. port bridge endpoint behavior into modular connector services instead of keeping it in the reference files
4. port workbook-driven chemistry logic into a versioned deterministic model module
5. add real LACRM, FreshBooks, Skimmer, and Heritage connector contracts

## Notes

- Live `.env` secrets were intentionally excluded.
- `bridge.db` was not used as runtime truth in this build.
- `legacy_bridge_reference/` is included to help continue the merge work safely.
