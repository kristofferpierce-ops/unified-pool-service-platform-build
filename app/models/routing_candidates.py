from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Field, SQLModel


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class RoutingPreferenceCandidate(SQLModel, table=True):
    """Platform-local routing candidate schema.

    Step 29 only defines the table shape and read-only API visibility.
    It intentionally does not import rows, write bridge rules, or call LACRM.
    """

    __tablename__ = "routing_preference_candidates"

    id: Optional[int] = Field(default=None, primary_key=True)
    preference_key: str = Field(index=True, sa_column_kwargs={"unique": True})
    phone: str = Field(index=True)
    proposed_mode: str = Field(default="manual", index=True)
    proposed_owner_type: str = Field(default="unknown", index=True)
    risk_level: str = Field(default="unknown", index=True)
    proposed_action: str = Field(default="")
    operator_decision: str = Field(default="unreviewed", index=True)
    import_blocker: str = Field(default="")
    eligible_for_future_dry_run_import: bool = Field(default=False, index=True)
    write_status: str = Field(default="schema_only_no_import", index=True)

    source_plan_path: str = Field(default="")
    source_preference_key: str = Field(default="")
    source_row_json: str = Field(default="{}")

    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
