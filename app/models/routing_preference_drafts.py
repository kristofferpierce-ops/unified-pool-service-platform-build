from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Field, SQLModel


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class RoutingPreferenceDraft(SQLModel, table=True):
    """Platform-local routing preference draft schema.

    Step 34 only defines the table shape and read-only API visibility.
    It intentionally does not create drafts, write bridge rules, or call LACRM.
    """

    __tablename__ = "routing_preference_drafts"

    id: Optional[int] = Field(default=None, primary_key=True)
    draft_key: str = Field(index=True, sa_column_kwargs={"unique": True})

    candidate_id: Optional[int] = Field(default=None, index=True)
    preference_key: str = Field(index=True)
    phone: str = Field(index=True)
    mode: str = Field(default="manual", index=True)
    owner_type: str = Field(default="unknown", index=True)
    label: str = Field(default="")
    default_contact_count: int = Field(default=0)

    status: str = Field(default="draft_schema_only", index=True)
    approval_source: str = Field(default="")
    operator_decision: str = Field(default="unreviewed", index=True)
    risk_level: str = Field(default="unknown", index=True)
    write_status: str = Field(default="draft_schema_only_no_write", index=True)

    source_candidate_json: str = Field(default="{}")
    source_reconciliation_json: str = Field(default="{}")

    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
