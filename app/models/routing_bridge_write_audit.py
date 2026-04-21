from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Field, SQLModel


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class RoutingBridgeWriteAudit(SQLModel, table=True):
    """Platform-local audit/rollback ledger for future bridge routing writes.

    Step 38 only defines the table shape and read-only API visibility.
    It intentionally does not create audit rows, write bridge rules, or call LACRM.
    """

    __tablename__ = "routing_bridge_write_audits"

    id: Optional[int] = Field(default=None, primary_key=True)

    audit_key: str = Field(index=True, sa_column_kwargs={"unique": True})
    rehearsal_idempotency_key: str = Field(default="", index=True)
    draft_id: Optional[int] = Field(default=None, index=True)
    draft_key: str = Field(default="", index=True)
    preference_key: str = Field(default="", index=True)

    phone: str = Field(default="", index=True)
    mode: str = Field(default="manual", index=True)
    owner_type: str = Field(default="unknown", index=True)
    label: str = Field(default="")

    bridge_endpoint: str = Field(default="/api/routing-rules")
    bridge_method: str = Field(default="POST")
    status: str = Field(default="audit_schema_only", index=True)

    request_payload_json: str = Field(default="{}")
    previous_bridge_rule_json: str = Field(default="{}")
    response_payload_json: str = Field(default="{}")
    rollback_payload_json: str = Field(default="{}")

    bridge_post_called: bool = Field(default=False, index=True)
    bridge_mutation_performed: bool = Field(default=False, index=True)
    platform_db_mutation_performed: bool = Field(default=False, index=True)
    lacrm_call_performed: bool = Field(default=False, index=True)

    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
