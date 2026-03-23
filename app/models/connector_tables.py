from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class SourceSystem(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    slug: str = Field(index=True, unique=True)
    display_name: str
    category: str = Field(default='connector', index=True)
    is_active: bool = True
    notes: str = ''
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ConnectorRun(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    source_system_id: Optional[int] = Field(default=None, index=True)
    source_slug: str = Field(index=True)
    run_type: str = Field(default='webhook', index=True)
    direction: str = Field(default='inbound', index=True)
    status: str = Field(default='received', index=True)
    raw_record_count: int = 0
    normalized_record_count: int = 0
    approved_count: int = 0
    applied_count: int = 0
    notes: str = ''
    started_at: datetime = Field(default_factory=datetime.utcnow)
    finished_at: Optional[datetime] = None


class RawSourceRecord(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    source_slug: str = Field(index=True)
    connector_run_id: Optional[int] = Field(default=None, index=True)
    external_id: str = Field(default='', index=True)
    record_type: str = Field(default='unknown', index=True)
    payload_json: str
    payload_hash: str = Field(default='', index=True)
    received_at: datetime = Field(default_factory=datetime.utcnow)
    status: str = Field(default='raw', index=True)


class NormalizedSourceRecord(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    raw_record_id: int = Field(index=True)
    source_slug: str = Field(index=True)
    entity_type: str = Field(index=True)
    normalized_json: str
    fingerprint: str = Field(default='', index=True)
    match_status: str = Field(default='pending', index=True)
    approval_status: str = Field(default='pending', index=True)
    apply_status: str = Field(default='pending', index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class MatchCandidate(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    normalized_record_id: int = Field(index=True)
    candidate_type: str = Field(index=True)
    candidate_ref: str = Field(index=True)
    score: float = 0.0
    reason: str = ''
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ApprovalDecision(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    normalized_record_id: int = Field(index=True)
    decided_by: str = Field(default='system', index=True)
    decision: str = Field(default='pending', index=True)
    decision_notes: str = ''
    approved_ref: str = ''
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ApplyEvent(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    normalized_record_id: int = Field(index=True)
    approval_decision_id: Optional[int] = Field(default=None, index=True)
    target_type: str = Field(default='internal_record', index=True)
    target_ref: str = Field(default='', index=True)
    outcome: str = Field(default='pending', index=True)
    details_json: str = '{}'
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ExternalIdentityMap(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    source_slug: str = Field(index=True)
    entity_type: str = Field(index=True)
    external_id: str = Field(index=True)
    internal_type: str = Field(index=True)
    internal_id: str = Field(index=True)
    confidence: float = 1.0
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
