from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class DevItem(SQLModel, table=True):
    """A single development-tracker entry.

    Powers the Development page (ui/pages/00_Development.py). One row is one of:
      - a working feature (what the platform actually does today),
      - a code-health finding (an architecture or quality issue from review),
      - an improvement idea / roadmap item (something to build).

    The table is intentionally self-contained and not linked to operational data,
    so it can be edited freely from the UI without touching production records.
    """

    __tablename__ = 'dev_item'

    id: Optional[int] = Field(default=None, primary_key=True)

    # 'feature' | 'health' | 'idea'
    category: str = Field(default='idea', index=True)

    title: str
    area: str = Field(default='General', index=True)

    # Status meaning depends on category:
    #   feature -> working | partial | stub
    #   health  -> open | in_progress | resolved | wont_fix
    #   idea    -> proposed | planned | in_progress | done | parked
    status: str = Field(default='proposed', index=True)

    # P0 (critical) .. P3 (nice to have); '-' for items where priority is not meaningful.
    priority: str = Field(default='P2', index=True)

    detail: str = Field(default='')
    source: str = Field(default='')  # where it came from: code review, market research, user, etc.

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class DevLogEntry(SQLModel, table=True):
    """One chronological changelog line for the Development page.

    Modeled on Lumen's build-stamped registry: every entry is tagged with a
    ``build`` (e.g. '2026.06.30-a') so shipped work groups into a clean,
    time-ordered log. Append-only in spirit; entries record what was actually
    built/changed each session so the history stays visually organized.

    Separate table from DevItem: DevItem tracks current STATE (features/health/
    ideas), DevLogEntry tracks the LOG (what happened, when, in which build).
    """

    __tablename__ = 'dev_log'

    id: Optional[int] = Field(default=None, primary_key=True)

    build: str = Field(default='', index=True)  # build stamp, e.g. '2026.06.30-a'

    # 'shipped' | 'fix' | 'refactor' | 'cleanup' | 'infra' | 'docs'
    kind: str = Field(default='shipped', index=True)

    area: str = Field(default='General', index=True)
    title: str = Field(default='')
    summary: str = Field(default='')

    logged_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
