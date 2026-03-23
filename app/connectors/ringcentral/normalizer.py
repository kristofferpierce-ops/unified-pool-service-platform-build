from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def _pick(*values: Any) -> str:
    for value in values:
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ''


def _iso_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def normalize_ringcentral_payload(payload: dict[str, Any]) -> dict[str, Any]:
    body = payload.get('body', payload)
    event = body.get('event', payload.get('event', ''))
    message = body.get('message', {})
    telephony_session_id = body.get('telephonySessionId') or body.get('sessionId') or ''
    caller_phone = _pick(
        body.get('from', {}).get('phoneNumber') if isinstance(body.get('from'), dict) else '',
        body.get('party', {}).get('from', {}).get('phoneNumber') if isinstance(body.get('party'), dict) else '',
        message.get('from', {}).get('phoneNumber') if isinstance(message.get('from'), dict) else '',
        payload.get('caller_phone', ''),
    )
    internal_phone = _pick(
        body.get('to', {}).get('phoneNumber') if isinstance(body.get('to'), dict) else '',
        message.get('to', [{}])[0].get('phoneNumber') if isinstance(message.get('to'), list) and message.get('to') else '',
        payload.get('internal_phone', ''),
    )
    occurred_at = _pick(body.get('creationTime'), body.get('eventTime'), message.get('creationTime'), payload.get('occurred_at')) or _iso_now()
    caller_name = _pick(
        body.get('from', {}).get('name') if isinstance(body.get('from'), dict) else '',
        message.get('from', {}).get('name') if isinstance(message.get('from'), dict) else '',
        payload.get('caller_name', ''),
    )

    text_body = _pick(message.get('subject', ''), message.get('body', ''), payload.get('summary', ''), payload.get('transcript', ''))
    names = caller_name
    address_hint = payload.get('extracted_address', '')

    lower_event = (event or '').lower()
    if 'message-store' in lower_event and 'sms' in lower_event:
        return {
            'entity_type': 'sms_message',
            'event_kind': 'sms',
            'external_id': _pick(message.get('id', ''), payload.get('external_id', '')),
            'message_external_id': _pick(message.get('id', ''), payload.get('external_id', '')),
            'external_phone': caller_phone,
            'internal_phone': internal_phone,
            'from_phone': caller_phone,
            'to_phone': internal_phone,
            'direction': _pick(message.get('direction', ''), payload.get('direction', 'Inbound')),
            'body': _pick(message.get('subject', ''), message.get('body', ''), payload.get('body', '')),
            'summary': text_body,
            'transcript': text_body,
            'caller_name': caller_name,
            'extracted_names': names,
            'extracted_address': address_hint,
            'occurred_at': occurred_at,
        }

    if 'voicemail' in lower_event or payload.get('item_type') == 'voicemail' or message.get('type') == 'VoiceMail':
        return {
            'entity_type': 'communication_event',
            'event_kind': 'voicemail',
            'external_id': _pick(message.get('id', ''), telephony_session_id, payload.get('external_id', '')),
            'voicemail_message_id': _pick(message.get('id', ''), payload.get('voicemail_message_id', '')),
            'external_phone': caller_phone,
            'internal_phone': internal_phone,
            'caller_name': caller_name,
            'direction': 'Inbound',
            'summary': text_body,
            'transcript': _pick(payload.get('transcript', ''), message.get('subject', ''), message.get('body', '')),
            'transcription_status': payload.get('voicemail_transcription_status', ''),
            'duration_seconds': int(payload.get('voicemail_duration', 0) or 0),
            'recording_uri': payload.get('voicemail_recording_uri', ''),
            'transcription_uri': payload.get('voicemail_transcription_uri', ''),
            'telephony_session_id': telephony_session_id,
            'agent_extension_id': payload.get('agent_extension_id', ''),
            'extracted_names': names,
            'extracted_address': address_hint,
            'occurred_at': occurred_at,
        }

    return {
        'entity_type': 'communication_event',
        'event_kind': 'call',
        'external_id': _pick(payload.get('rc_event_uuid', ''), telephony_session_id, payload.get('external_id', '')),
        'telephony_session_id': telephony_session_id,
        'external_phone': caller_phone,
        'internal_phone': internal_phone,
        'caller_name': caller_name,
        'direction': _pick(payload.get('direction', ''), body.get('direction', ''), 'Inbound'),
        'summary': _pick(payload.get('summary', ''), text_body),
        'transcript': _pick(payload.get('transcript', ''), text_body),
        'recording_uri': payload.get('recording_uri', ''),
        'agent_extension_id': payload.get('agent_extension_id', ''),
        'disposition': payload.get('status', ''),
        'extracted_names': names,
        'extracted_address': address_hint,
        'occurred_at': occurred_at,
    }
