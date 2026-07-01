"""Routes as first-class entities, linked to the service visits they contain.

Skimmer routes arrive in the ledger with a list of work-order ids; applying them
here (RouteRecord + RouteVisit links) lets route-level P&L roll up the cost and
allocated revenue of the visits on each route.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class RouteRecord(SQLModel, table=True):
    __tablename__ = 'route_record'

    id: Optional[int] = Field(default=None, primary_key=True)
    source_slug: str = Field(default='skimmer', index=True)
    external_id: str = Field(default='', index=True)
    name: str = ''
    route_date: Optional[date] = Field(default=None, index=True)
    technician: str = Field(default='', index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class RouteVisit(SQLModel, table=True):
    __tablename__ = 'route_visit'

    id: Optional[int] = Field(default=None, primary_key=True)
    route_id: int = Field(index=True)
    service_visit_id: int = Field(index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
