"""Unified customer identity + cross-system match records.

A CustomerProfile is the canonical customer (one per internal Account), carrying
the contact keys (email/phone) used to match external records to it. A
CustomerMatch records how an external record (a Skimmer customer, a FreshBooks
client) resolved to an account -- which pass matched it, the confidence, any
candidate suggestions, and whether a human confirmed/overrode it.

This is the join that lets Skimmer-fed COST and FreshBooks-fed REVENUE land on
the same customer for profitability.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class CustomerProfile(SQLModel, table=True):
    __tablename__ = 'customer_profile'

    id: Optional[int] = Field(default=None, primary_key=True)
    account_id: int = Field(index=True, unique=True)

    display_name: str = Field(default='', index=True)
    email: str = Field(default='', index=True)
    phone: str = Field(default='', index=True)
    company_name: str = ''
    primary_source: str = ''  # who created this profile: skimmer | freshbooks | manual

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class CustomerMatch(SQLModel, table=True):
    __tablename__ = 'customer_match'

    id: Optional[int] = Field(default=None, primary_key=True)

    source_slug: str = Field(index=True)          # skimmer | freshbooks | ...
    external_id: str = Field(default='', index=True)

    # Denormalized external contact info for the review queue.
    external_name: str = ''
    external_email: str = Field(default='', index=True)
    external_phone: str = ''
    external_company: str = ''

    account_id: Optional[int] = Field(default=None, index=True)  # resolved account, or None if unmatched

    # 0 unmatched, 1 exact, 2 assisted, 3 manual
    match_pass: int = Field(default=0, index=True)
    # auto | suggested | manual | unmatched  (+ confirmed once a human accepts/overrides)
    status: str = Field(default='unmatched', index=True)
    confidence: float = 0.0
    candidates_json: str = '[]'   # [{account_id, name, score, reason}, ...] for suggested/manual review
    notes: str = ''

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
