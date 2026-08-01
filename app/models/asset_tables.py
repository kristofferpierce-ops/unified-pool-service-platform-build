"""Physical asset registry: track a real item through its lifecycle.

A pool pump (or heater, filter, salt cell, light, controller) as it moves:
    ordered -> received -> installed -> retired
capturing serial/model numbers, purchase provenance (vendor, invoice, cost),
where it ended up (property + vessel), and warranty. This builds the asset list
that lives in each property's profile.

New table (not the thin legacy EquipmentAsset) so it creates cleanly on existing
SQLite DBs without a column migration.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class AssetRecord(SQLModel, table=True):
    __tablename__ = 'asset_record'

    id: Optional[int] = Field(default=None, primary_key=True)

    name: str = ''
    category: str = Field(default='pump', index=True)  # pump|heater|filter|salt_cell|light|controller|pump_motor|other

    manufacturer: str = ''
    model_number: str = Field(default='', index=True)
    serial_number: str = Field(default='', index=True)

    # ordered | received | installed | retired
    status: str = Field(default='ordered', index=True)

    # Where it lives once installed.
    property_id: Optional[int] = Field(default=None, index=True)
    vessel_id: Optional[int] = Field(default=None, index=True)

    # Purchase provenance.
    vendor_name: str = ''
    vendor_id: Optional[int] = Field(default=None, index=True)  # -> Vendor (Tier 2; additive, keeps string)
    invoice_number: str = ''
    purchase_cost: float = 0.0

    # Lifecycle dates.
    purchase_date: Optional[date] = None
    received_date: Optional[date] = None
    install_date: Optional[date] = None
    retirement_date: Optional[date] = None
    warranty_until: Optional[date] = None

    notes: str = ''

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
