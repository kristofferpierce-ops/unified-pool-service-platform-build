"""Vendor identity spine (QuickBooks Tier 2). Mirrors the customer spine
(``customer_tables.py``) so suppliers get the same never-orphan, flag-duplicates
resolution that unified 447 customers -- built as parallel tables, with zero
changes to the live customer code.

A ``Vendor`` is the canonical supplier (its ``name`` is the immutable natural key
QuickBooks transactions reference). ``VendorProfile`` carries the match keys; a
vendor's TAXID is never stored here in plaintext -- only a keyed hash (for dedup)
and a masked last-4 (for display); the encrypted full value lives once in the
``RawSourceCell`` vault. ``VendorMatch`` records how an external record resolved,
for review/override. Tier 3 bills will reference ``vendor_id``.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class Vendor(SQLModel, table=True):
    __tablename__ = 'vendor'

    id: Optional[int] = Field(default=None, primary_key=True)
    vendor_type: str = Field(default='supplier', index=True)
    name: str = Field(index=True)              # immutable natural key = raw IIF NAME
    billing_name: str = ''                     # PRINTAS ("print on check as")
    notes: str = ''
    address_block: str = ''                    # ADDR1..5 kept verbatim as one block
    is_active: bool = Field(default=True, index=True)   # HIDDEN=Y -> False (excluded from auto-match)

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class VendorProfile(SQLModel, table=True):
    __tablename__ = 'vendor_profile'

    id: Optional[int] = Field(default=None, primary_key=True)
    vendor_id: int = Field(index=True, unique=True)

    display_name: str = Field(default='', index=True)   # company or printas or person or name
    company_name: str = ''
    person_name: str = ''                      # resolution key when company blank
    email: str = Field(default='', index=True)
    phone: str = Field(default='', index=True)
    tax_id_hash: str = Field(default='', index=True)    # keyed HMAC of normalized TAXID (Pass-1 key)
    tax_id_last4: str = ''                      # masked display only
    terms: str = ''
    is_1099: bool = Field(default=False, index=True)
    is_active: bool = Field(default=True, index=True)
    primary_source: str = ''                   # quickbooks | manual
    source_artifact_id: Optional[int] = Field(default=None, index=True)   # -> RawSourceCell vault
    source_row_id: Optional[int] = Field(default=None, index=True)

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class VendorMatch(SQLModel, table=True):
    __tablename__ = 'vendor_match'

    id: Optional[int] = Field(default=None, primary_key=True)

    source_slug: str = Field(index=True)       # quickbooks | manual | ...
    external_id: str = Field(default='', index=True)   # IIF REFNUM, fallback NAME

    external_name: str = ''
    external_email: str = Field(default='', index=True)
    external_phone: str = ''
    external_company: str = ''
    external_tax_id_hash: str = Field(default='', index=True)

    vendor_id: Optional[int] = Field(default=None, index=True)   # resolved vendor, None if unmatched

    # 0 unmatched, 1 exact tax-id/new, 2 assisted, 3 manual
    match_pass: int = Field(default=0, index=True)
    # auto | flagged | suggested | unmatched  (+ confirmed once a human accepts/overrides)
    status: str = Field(default='unmatched', index=True)
    confidence: float = 0.0
    candidates_json: str = '[]'
    notes: str = ''

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
