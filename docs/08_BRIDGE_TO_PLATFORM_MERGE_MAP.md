# Bridge to platform merge map

## What to keep from the bridge

### RingCentral side
Keep and refactor:
- webhook receipt logic
- subscription setup logic
- call and voicemail enrichment logic
- message sync logic
- event dedupe logic

Move to:
- `app/connectors/ringcentral/`

### LACRM side
Keep and refactor:
- contact search logic
- note creation logic
- task creation logic
- attached timeline helpers
- candidate scoring helpers

Move to:
- `app/connectors/lacrm/`

### Front desk workflow side
Keep and refactor:
- queue review behavior
- attach flow
- trash or dismiss flow
- incoming caller context HUD
- routing rule editing
- task creation actions

Move to:
- unified platform UI pages and APIs
- canonical communication event domain

## What not to keep as-is
- single-file backend architecture in `main.py`
- bridge SQLite persistence as production truth
- live secrets from `.env`
- direct external-write assumptions as canonical truth
- duplicate JS or CSS variants unless a specific diff is needed

## Bridge database migration intent
Current bridge tables map roughly like this:

- `calls` → `communication_event`, `call_session`, `voicemail_item`
- `sms_batches` → `sms_thread`
- `sms_messages` → `sms_message`
- `caller_relationships` → `contact_match_candidate` or operator affinity memory
- `routing_rules` → `routing_preference`
- `processed_event_uuids` → `connector_run` and raw event idempotency support
- `message_sync_state` → connector sync cursor state

## Net result
The bridge is not a separate future product line.
It is the communications and intake seed for the unified operating core.
