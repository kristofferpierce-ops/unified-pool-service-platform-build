# RingCentral → Less Annoying CRM bridge starter

This starter now supports **three communication workflows** in the same UI:

1. **Calls + voicemail**: RingCentral telephony events, live ringing HUD, and voicemail intake pushed into the same front-desk review queue.
2. **Text summaries**: daily SMS batches grouped by outside phone number, with routing rules so you can keep property managers manual and let homeowner numbers auto-attach.
3. **Voicemail clue extraction + auto-save**: voicemail transcription or voicemail subject text is analyzed for names and addresses, then matched against LACRM for review or auto-attach.

## What changed

### SMS batching UI
- New **Text summaries** tab next to Calls.
- **Run end-of-day text batch now** button in the header.
- **Force batch now** button on an open SMS thread so staff can summarize the current conversation immediately.
- Per-number routing rules shown in the UI:
  - **Require manual approval**
  - **Set auto homeowner** on a selected LACRM match
  - **Save PM property** on a selected LACRM match

### Routing rule behavior
- **Homeowner / auto**: one default contact ID, current and future SMS summaries for that phone auto-attach.
- **Property manager / manual**: saves favorite property/contact IDs but still requires a human to choose where the note goes.
- Candidate scoring boosts:
  - previous manual selections
  - saved property-manager favorites
  - phone/address/name clues extracted from the thread

### End-of-day batching
- The app groups texts by **external phone number + local date**.
- A background loop checks the local server time and auto-runs end-of-day batching at:
  - `SMS_BATCH_HOUR_LOCAL`
  - `SMS_BATCH_MINUTE_LOCAL`
- You can also trigger it manually from the UI or by calling:
  - `POST /api/admin/run_sms_eod`

## RingCentral permissions to plan for

### Calls (existing flow)
- `SubscriptionWebhook`
- `CallControl`
- `RingSense` (for summaries / transcripts)

### SMS batching
- `SubscriptionWebhook`
- `ReadMessages`

### Voicemail intake
- `SubscriptionWebhook`
- `ReadMessages`
- RingCentral voicemail-to-text enabled if you want transcript attachments; when not available, the app falls back to the voicemail subject text.

## Important note about live SMS events
The starter includes the subscription filter:

- `/restapi/v1.0/account/~/extension/~/message-store/instant?type=SMS`

That is the simplest live path for inbound SMS events.
If you also want guaranteed outbound capture from RingCentral, you may later add a Message Store sync/poll step using the Message Store API.

## Useful endpoints

### Main UI
- `/`

### Calls
- `GET /api/calls`
- `GET /api/calls/{call_id}`
- `GET /api/calls/{call_id}/candidates`
- `POST /api/calls/{call_id}/attach`

### SMS batches
- `GET /api/sms/batches`
- `GET /api/sms/batches/{batch_id}`
- `GET /api/sms/batches/{batch_id}/candidates`
- `POST /api/sms/batches/{batch_id}/force_batch`
- `POST /api/sms/batches/{batch_id}/attach`

### Routing rules
- `GET /api/routing-rules?phone=...`
- `POST /api/routing-rules`

### Admin / setup
- `POST /api/admin/create_subscription`
- `POST /api/admin/run_sms_eod`

### Demo / testing
- `POST /api/test/sms_seed`

## Demo SMS seed example
Use `/docs` and post to `POST /api/test/sms_seed` with a payload like this:

```json
{
  "external_phone": "+13055551212",
  "internal_phone": "+13055550000",
  "messages": [
    {
      "direction": "Inbound",
      "message_time": "2026-02-28T13:00:00Z",
      "body": "Hi, this is Mike at 123 Palm Ave. Heater is still down."
    },
    {
      "direction": "Outbound",
      "message_time": "2026-02-28T13:12:00Z",
      "body": "We are checking schedule options and will confirm today."
    }
  ]
}
```

That will create a test SMS batch so you can verify:
- the SMS queue
- forced batch refresh
- candidate matching
- homeowner auto-attach vs manual PM review

## Monday restart reminder
Keep these running:
- the Python app (`python main.py`)
- ngrok

If ngrok changes its forwarding URL, update `RC_WEBHOOK_PUBLIC_URL` and restart the Python app.


## Live subscription troubleshooting

This project now supports targeted subscription testing from `/docs`:

- `POST /api/admin/create_subscription?mode=calls`
- `POST /api/admin/create_subscription?mode=sms`
- `POST /api/admin/create_subscription?mode=core` (calls + sms, no RingSense)
- `POST /api/admin/create_subscription?mode=all`
- `GET /api/admin/subscription_preview?mode=core`

Recommended order for live testing:
1. Start with `mode=calls`
2. Then try `mode=sms`
3. Then try `mode=voicemail`
4. Then `mode=core`
5. Only turn on RingSense after the other three are working

The webhook builder now automatically appends `?secret=...` when `RC_WEBHOOK_SHARED_SECRET` is set.
Calls no longer require recordings unless `CALLS_REQUIRE_RECORDINGS=true` is set in `.env`.


## Important Swagger note
Use the `mode` as a **query parameter** when calling `POST /api/admin/create_subscription` from `/docs`.
Do not send it in the request body. For example: `POST /api/admin/create_subscription?mode=calls`.


## Tier 1 UI improvements included
- confirmation pop-ups before CRM/routing actions that are hard to undo
- question-mark help buttons with plain-English explanations
- clearer queue badges for confirmed/manual/auto/multiple states
- success toast messages after attach and routing changes


## Help buttons
The ? icons now work in two ways:
- hover shows the browser tooltip
- click opens the in-app help modal
If you do not see the new behavior, hard-refresh the browser with Ctrl+F5.


## Tier 2 additions

- **Create task** buttons now appear on call and text detail views and candidate rows.
- After attaching a conversation to a CRM contact, the UI can immediately prompt you to create a follow-up task.
- Task creation uses Less Annoying CRM's task flow with optional assignee, due date, and description.
- **Trash / dismiss** buttons hide spam or junk calls/text batches from the working queue without sending them to CRM.

### New API routes

- `GET /api/lacrm/users`
- `POST /api/calls/{call_id}/task`
- `POST /api/sms/batches/{batch_id}/task`
- `POST /api/calls/{call_id}/trash`
- `POST /api/sms/batches/{batch_id}/trash`


## Incoming ringing HUD

- The call subscription now listens to telephony session updates so the app can show a heads-up panel while the phone is ringing.
- Keep the browser open on the main page to see the live caller context panel.
- The HUD uses the incoming phone number to find the most likely LACRM match and shows the last five CRM items for that profile.
- If you refresh or recreate the RingCentral subscription after updating, use the same `POST /api/admin/create_subscription?mode=calls` endpoint.


## Voicemail workflow

- The project can subscribe to RingCentral's **Voicemail Message Event** using `mode=voicemail` or `mode=core`.
- When a voicemail arrives, the app tries to read the `AudioTranscription` attachment if RingCentral has completed voicemail-to-text; if not, it falls back to the voicemail `subject` text.
- The app then extracts address/name clues, scores LACRM contacts, and will **auto-attach** the voicemail when confidence is high enough or when a homeowner auto-rule already exists for that number.
- Lower-confidence voicemail items stay in the normal Calls + voicemail review queue for a human to confirm.
- Voicemails appear in the **Calls + voicemail** lane and can still be tasked, trashed, or reviewed in processed history after they are attached.


## Voicemail transcription timing

RingCentral voicemail events often arrive before voicemail-to-text transcription is ready. This build polls the message-store item for a short period and updates the voicemail transcript and extracted clues once an `AudioTranscription` attachment becomes available.

Optional .env tuning:

- `VOICEMAIL_TRANSCRIPT_INITIAL_SECONDS` (default 10)
- `VOICEMAIL_TRANSCRIPT_MAX_ATTEMPTS` (default 18)




## Full SMS conversation (Inbound + Outbound)

RingCentral's **Instant SMS event** (`/message-store/instant?type=SMS`) only notifies on **inbound** SMS.
To show a complete conversation thread (including **outbound** messages sent by the office), this project uses the **Message Sync API**
to continuously sync SMS messages (both directions) and insert them into the local database.

Environment knobs:
- `ENABLE_SMS_SYNC=true`
- `SMS_SYNC_POLL_SECONDS=20`
- `SMS_SYNC_LOOKBACK_DAYS=7`

