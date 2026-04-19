from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def _pick(*values: Any) -> str:
    for value in values:
        if isinstance(value, str) and value.strip():
            return value.strip()
        if value is not None and not isinstance(value, (dict, list, tuple, set)):
            text = str(value).strip()
            if text:
                return text
    return ''


def _iso_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if value:
        return [value]
    return []


def _phone(endpoint: Any) -> str:
    endpoint = _as_dict(endpoint)
    return _pick(endpoint.get('phoneNumber'), endpoint.get('phone'), endpoint.get('extensionNumber'))


def _name(endpoint: Any) -> str:
    endpoint = _as_dict(endpoint)
    return _pick(endpoint.get('name'), endpoint.get('displayName'))


def _message_record(payload: dict[str, Any], body: dict[str, Any]) -> dict[str, Any]:
    """Return the RingCentral message object whether it is nested or direct.

    Webhook samples often look like body.message, while Message Sync records and the
    standalone bridge can pass the message fields directly under body.
    """
    nested = body.get('message')
    if isinstance(nested, dict):
        return nested
    return body


def _first_to_phone(message: dict[str, Any]) -> str:
    for item in _as_list(message.get('to')):
        phone = _phone(item)
        if phone:
            return phone
    return ''


def _external_to_phone(message: dict[str, Any], internal_phone: str) -> str:
    internal = ''.join(ch for ch in (internal_phone or '') if ch.isdigit())
    fallback = ''
    for item in _as_list(message.get('to')):
        phone = _phone(item)
        if not fallback and phone:
            fallback = phone
        digits = ''.join(ch for ch in phone if ch.isdigit())
        if phone and digits != internal:
            return phone
    return fallback


def _extract_party_phones(body: dict[str, Any]) -> tuple[str, str, str, str]:
    caller_phone = ''
    internal_phone = ''
    agent_extension_id = ''
    caller_name = ''
    for party in _as_list(body.get('parties')):
        party = _as_dict(party)
        from_ep = _as_dict(party.get('from'))
        to_ep = _as_dict(party.get('to'))
        if not caller_phone and _phone(from_ep) and not from_ep.get('extensionId'):
            caller_phone = _phone(from_ep)
            caller_name = _name(from_ep)
        if not caller_phone and _phone(to_ep) and not to_ep.get('extensionId'):
            caller_phone = _phone(to_ep)
            caller_name = _name(to_ep)
        if not internal_phone and _phone(to_ep) and to_ep.get('extensionId'):
            internal_phone = _phone(to_ep)
            agent_extension_id = _pick(to_ep.get('extensionId'))
        if not internal_phone and _phone(from_ep) and from_ep.get('extensionId'):
            internal_phone = _phone(from_ep)
            agent_extension_id = _pick(from_ep.get('extensionId'))
        if not agent_extension_id and party.get('extensionId'):
            agent_extension_id = _pick(party.get('extensionId'))
    return caller_phone, internal_phone, agent_extension_id, caller_name


def normalize_ringcentral_payload(payload: dict[str, Any]) -> dict[str, Any]:
    body = _as_dict(payload.get('body')) or payload
    event = _pick(body.get('event'), payload.get('event'))
    message = _message_record(payload, body)
    lower_event = (event or '').lower()
    message_type = _pick(message.get('type'), body.get('type'), payload.get('type'))

    telephony_session_id = _pick(body.get('telephonySessionId'), body.get('sessionId'), body.get('sourceSessionId'))
    party_caller_phone, party_internal_phone, party_agent_extension_id, party_caller_name = _extract_party_phones(body)

    occurred_at = _pick(
        body.get('creationTime'),
        body.get('eventTime'),
        body.get('recordingStartTime'),
        message.get('creationTime'),
        message.get('lastModifiedTime'),
        payload.get('timestamp'),
        payload.get('occurred_at'),
    ) or _iso_now()

    message_text = _pick(message.get('subject'), message.get('body'), body.get('subject'), body.get('body'), payload.get('summary'), payload.get('transcript'))
    caller_name = _pick(
        _name(message.get('from')),
        _name(body.get('from')),
        party_caller_name,
        payload.get('caller_name'),
    )

    names = caller_name
    address_hint = payload.get('extracted_address', '')

    is_sms = (
        ('message-store' in lower_event and 'sms' in lower_event)
        or str(message_type).lower() == 'sms'
        or payload.get('event_kind') == 'sms'
    )
    if is_sms:
        direction = _pick(message.get('direction'), body.get('direction'), payload.get('direction'), 'Inbound')
        from_phone = _phone(message.get('from')) or _phone(body.get('from'))
        if direction.lower() == 'outbound':
            internal_phone = _pick(from_phone, payload.get('internal_phone'))
            external_phone = _pick(_external_to_phone(message, internal_phone), payload.get('external_phone'))
        else:
            external_phone = _pick(from_phone, payload.get('external_phone'))
            internal_phone = _pick(_first_to_phone(message), payload.get('internal_phone'))

        return {
            'entity_type': 'sms_message',
            'event_kind': 'sms',
            'external_id': _pick(message.get('id'), body.get('id'), payload.get('external_id'), payload.get('uuid')),
            'message_external_id': _pick(message.get('id'), body.get('id'), payload.get('external_id'), payload.get('uuid')),
            'external_phone': external_phone,
            'internal_phone': internal_phone,
            'from_phone': from_phone,
            'to_phone': _first_to_phone(message),
            'direction': direction,
            'body': message_text,
            'summary': message_text,
            'transcript': message_text,
            'caller_name': caller_name,
            'extracted_names': names,
            'extracted_address': address_hint,
            'occurred_at': occurred_at,
            'bridge_context': payload.get('bridge_context', {}),
        }

    is_voicemail = (
        'voicemail' in lower_event
        or payload.get('item_type') == 'voicemail'
        or str(message_type).lower() in {'voicemail', 'voice_mail', 'voiceMail'.lower()}
        or str(message_type) == 'VoiceMail'
    )
    if is_voicemail:
        attachments = _as_list(message.get('attachments') or body.get('attachments'))
        recording_uri = payload.get('voicemail_recording_uri', '')
        transcription_uri = payload.get('voicemail_transcription_uri', '')
        duration = payload.get('voicemail_duration', 0) or 0
        for attachment in attachments:
            attachment = _as_dict(attachment)
            attachment_type = str(attachment.get('type') or '').lower()
            if attachment_type == 'audiorecording':
                recording_uri = _pick(recording_uri, attachment.get('uri'))
                duration = duration or attachment.get('vmDuration') or 0
            if attachment_type == 'audiotranscription':
                transcription_uri = _pick(transcription_uri, attachment.get('uri'))

        return {
            'entity_type': 'communication_event',
            'event_kind': 'voicemail',
            'external_id': _pick(message.get('id'), body.get('id'), telephony_session_id, payload.get('external_id'), payload.get('uuid')),
            'voicemail_message_id': _pick(message.get('id'), body.get('id'), payload.get('voicemail_message_id')),
            'external_phone': _pick(_phone(message.get('from')), _phone(body.get('from')), party_caller_phone, payload.get('external_phone')),
            'internal_phone': _pick(_first_to_phone(message), _first_to_phone(body), party_internal_phone, payload.get('internal_phone')),
            'caller_name': caller_name,
            'direction': 'Inbound',
            'summary': message_text,
            'transcript': _pick(payload.get('transcript'), message_text),
            'transcription_status': _pick(payload.get('voicemail_transcription_status'), message.get('vmTranscriptionStatus'), body.get('vmTranscriptionStatus')),
            'duration_seconds': int(duration or 0),
            'recording_uri': recording_uri,
            'transcription_uri': transcription_uri,
            'telephony_session_id': telephony_session_id,
            'agent_extension_id': _pick(party_agent_extension_id, payload.get('agent_extension_id')),
            'extracted_names': names,
            'extracted_address': address_hint,
            'occurred_at': occurred_at,
            'bridge_context': payload.get('bridge_context', {}),
        }

    # Telephony session or RingSense insight events both materialize as call events.
    caller_phone = _pick(
        _phone(body.get('from')),
        _phone(_as_dict(body.get('party')).get('from')),
        party_caller_phone,
        _phone(message.get('from')),
        payload.get('caller_phone'),
    )
    internal_phone = _pick(
        _phone(body.get('to')),
        _phone(_as_dict(body.get('party')).get('to')),
        party_internal_phone,
        _first_to_phone(message),
        payload.get('internal_phone'),
    )
    source_record_id = _pick(body.get('sourceRecordId'), payload.get('source_record_id'))
    source_session_id = _pick(body.get('sourceSessionId'), telephony_session_id)

    return {
        'entity_type': 'communication_event',
        'event_kind': 'call',
        'external_id': _pick(payload.get('uuid'), source_record_id, source_session_id, telephony_session_id, payload.get('external_id')),
        'telephony_session_id': _pick(source_session_id, telephony_session_id),
        'source_record_id': source_record_id,
        'external_phone': caller_phone,
        'internal_phone': internal_phone,
        'caller_name': caller_name,
        'direction': _pick(payload.get('direction'), body.get('direction'), body.get('callDirection'), 'Inbound'),
        'summary': _pick(payload.get('summary'), body.get('summary'), body.get('brief'), message_text),
        'transcript': _pick(payload.get('transcript'), body.get('transcript'), message_text),
        'recording_uri': _pick(payload.get('recording_uri'), body.get('recordingUri')),
        'agent_extension_id': _pick(party_agent_extension_id, payload.get('agent_extension_id')),
        'disposition': _pick(payload.get('status'), body.get('status'), body.get('sessionStatus'), body.get('telephonyStatus')),
        'extracted_names': names,
        'extracted_address': address_hint,
        'occurred_at': occurred_at,
        'bridge_context': payload.get('bridge_context', {}),
    }
