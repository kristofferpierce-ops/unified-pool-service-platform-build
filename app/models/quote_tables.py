from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class QuoteCase(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    quote_number: str = Field(default='', index=True, unique=True)
    pipeline_slug: str = Field(index=True)
    stage_slug: str = Field(index=True)
    workflow_mode: str = Field(default='quote', index=True)
    account_id: Optional[int] = Field(default=None, index=True)
    property_id: Optional[int] = Field(default=None, index=True)
    vessel_id: Optional[int] = Field(default=None, index=True)
    title: str = Field(index=True)
    requester_name: str = Field(default='', index=True)
    requester_phone: str = ''
    requester_email: str = ''
    description: str = ''
    assigned_to: str = Field(default='', index=True)
    freshbooks_status: str = Field(default='not_created', index=True)
    is_viewed: bool = False
    last_viewed_at: Optional[datetime] = None
    follow_up_due_on: Optional[date] = Field(default=None, index=True)
    requested_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    stage_entered_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    sync_status: str = Field(default='local_only', index=True)
    sync_notes: str = ''
    last_synced_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class QuoteStageHistory(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    quote_case_id: int = Field(index=True)
    pipeline_slug: str = Field(index=True)
    from_stage_slug: str = Field(default='', index=True)
    to_stage_slug: str = Field(index=True)
    moved_by: str = Field(default='system', index=True)
    move_reason: str = ''
    moved_at: datetime = Field(default_factory=datetime.utcnow, index=True)


class QuoteCaseExternalLink(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    quote_case_id: int = Field(index=True)
    system_slug: str = Field(index=True)
    external_type: str = Field(default='record', index=True)
    external_id: str = Field(index=True)
    external_label: str = ''
    sync_direction: str = Field(default='bidirectional', index=True)
    sync_status: str = Field(default='pending', index=True)
    payload_json: str = '{}'
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
