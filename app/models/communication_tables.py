from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class CommunicationEvent(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    normalized_record_id: Optional[int] = Field(default=None, index=True)
    source_slug: str = Field(default='ringcentral', index=True)
    event_kind: str = Field(index=True)
    external_phone: str = Field(default='', index=True)
    internal_phone: str = ''
    caller_name: str = Field(default='', index=True)
    occurred_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    status: str = Field(default='pending_review', index=True)
    extracted_address: str = ''
    extracted_names: str = ''
    summary: str = ''
    transcript: str = ''
    raw_json: str = '{}'


class CallSession(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    communication_event_id: int = Field(index=True)
    telephony_session_id: str = Field(default='', index=True)
    direction: str = Field(default='', index=True)
    agent_extension_id: str = ''
    recording_uri: str = ''
    disposition: str = ''


class VoicemailItem(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    communication_event_id: int = Field(index=True)
    voicemail_message_id: str = Field(default='', index=True)
    duration_seconds: int = 0
    transcription_status: str = ''
    recording_uri: str = ''
    transcription_uri: str = ''


class SMSThread(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    normalized_record_id: Optional[int] = Field(default=None, index=True)
    external_phone: str = Field(index=True)
    internal_phone: str = ''
    local_day: date = Field(default_factory=date.today, index=True)
    latest_message_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    status: str = Field(default='pending_review', index=True)
    summary: str = ''
    transcript: str = ''
    extracted_address: str = ''
    extracted_names: str = ''
    auto_attached: bool = False
    raw_json: str = '{}'


class SMSMessage(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    sms_thread_id: int = Field(index=True)
    message_external_id: str = Field(default='', index=True)
    direction: str = ''
    from_phone: str = ''
    to_phone: str = ''
    body: str = ''
    occurred_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    raw_json: str = '{}'


class RoutingPreference(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    phone: str = Field(index=True, unique=True)
    route_mode: str = Field(default='manual', index=True)
    default_contact_ref: str = ''
    favorite_refs_json: str = '[]'
    notes: str = ''
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class ContactMatchCandidate(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    communication_event_id: Optional[int] = Field(default=None, index=True)
    sms_thread_id: Optional[int] = Field(default=None, index=True)
    contact_ref: str = Field(index=True)
    display_label: str
    score: float = 0.0
    reasoning: str = ''
    is_selected: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)


class OperatorDecision(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    communication_event_id: Optional[int] = Field(default=None, index=True)
    sms_thread_id: Optional[int] = Field(default=None, index=True)
    decision: str = Field(default='pending', index=True)
    chosen_contact_ref: str = ''
    notes: str = ''
    decided_by: str = Field(default='operator', index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class CRMApplyAction(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    operator_decision_id: Optional[int] = Field(default=None, index=True)
    action_type: str = Field(index=True)
    target_contact_ref: str = Field(default='', index=True)
    payload_json: str = '{}'
    status: str = Field(default='pending', index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class CommunicationTaskLink(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    communication_event_id: Optional[int] = Field(default=None, index=True)
    sms_thread_id: Optional[int] = Field(default=None, index=True)
    crm_apply_action_id: Optional[int] = Field(default=None, index=True)
    title: str
    due_date: Optional[date] = None
    assignee_ref: str = ''
    status: str = Field(default='open', index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
