"""Asset lifecycle service: create, advance, and report on physical assets.

Drives an AssetRecord through ordered -> received -> installed -> retired,
stamping the date at each step and binding it to a property/vessel on install.
Also rolls up the installed base and flags warranty expirations.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime

from sqlmodel import Session, select

from app.models.asset_tables import AssetRecord

ASSET_STATUSES = ['ordered', 'received', 'installed', 'retired']
ASSET_CATEGORIES = [
    'pump', 'pump_motor', 'heater', 'filter', 'salt_cell',
    'light', 'controller', 'cleaner', 'other',
]


def _touch(asset: AssetRecord) -> None:
    asset.updated_at = datetime.utcnow()


def create_asset(
    session: Session,
    *,
    name: str,
    category: str = 'pump',
    manufacturer: str = '',
    model_number: str = '',
    serial_number: str = '',
    vendor_name: str = '',
    invoice_number: str = '',
    purchase_cost: float = 0.0,
    purchase_date: date | None = None,
    status: str = 'ordered',
    notes: str = '',
) -> AssetRecord:
    asset = AssetRecord(
        name=name,
        category=category,
        manufacturer=manufacturer,
        model_number=model_number,
        serial_number=serial_number,
        vendor_name=vendor_name,
        invoice_number=invoice_number,
        purchase_cost=purchase_cost,
        purchase_date=purchase_date,
        status=status if status in ASSET_STATUSES else 'ordered',
        notes=notes,
    )
    session.add(asset)
    session.commit()
    session.refresh(asset)
    return asset


def _get(session: Session, asset_id: int) -> AssetRecord:
    asset = session.get(AssetRecord, asset_id)
    if not asset:
        raise ValueError('Asset not found')
    return asset


def receive_asset(session: Session, asset_id: int, received_date: date | None = None) -> AssetRecord:
    asset = _get(session, asset_id)
    asset.status = 'received'
    asset.received_date = received_date or date.today()
    _touch(asset)
    session.commit()
    session.refresh(asset)
    return asset


def install_asset(
    session: Session,
    asset_id: int,
    *,
    property_id: int,
    vessel_id: int | None = None,
    install_date: date | None = None,
    warranty_until: date | None = None,
) -> AssetRecord:
    asset = _get(session, asset_id)
    asset.status = 'installed'
    asset.property_id = property_id
    asset.vessel_id = vessel_id
    asset.install_date = install_date or date.today()
    if warranty_until is not None:
        asset.warranty_until = warranty_until
    _touch(asset)
    session.commit()
    session.refresh(asset)
    return asset


def retire_asset(session: Session, asset_id: int, retirement_date: date | None = None, reason: str = '') -> AssetRecord:
    asset = _get(session, asset_id)
    asset.status = 'retired'
    asset.retirement_date = retirement_date or date.today()
    if reason:
        asset.notes = (asset.notes + f'\nRetired: {reason}').strip()
    _touch(asset)
    session.commit()
    session.refresh(asset)
    return asset


def list_assets(
    session: Session,
    status: str | None = None,
    property_id: int | None = None,
    category: str | None = None,
) -> list[AssetRecord]:
    rows = list(session.exec(select(AssetRecord)).all())
    if status:
        rows = [a for a in rows if a.status == status]
    if property_id is not None:
        rows = [a for a in rows if a.property_id == property_id]
    if category:
        rows = [a for a in rows if a.category == category]
    # Active (non-retired) first, then newest.
    rows.sort(key=lambda a: (a.status == 'retired', -(a.id or 0)))
    return rows


def assets_for_property(session: Session, property_id: int) -> list[AssetRecord]:
    return list_assets(session, property_id=property_id)


@dataclass
class AssetSummary:
    total: int
    by_status: dict = field(default_factory=dict)
    by_category: dict = field(default_factory=dict)
    installed_count: int = 0
    installed_base_value: float = 0.0      # sum of purchase_cost for installed assets
    in_warranty: int = 0                   # installed assets whose warranty_until >= today
    warranty_expiring_soon: int = 0        # in-warranty and expiring within `soon_days`


def asset_summary(session: Session, soon_days: int = 60, today: date | None = None) -> AssetSummary:
    today = today or date.today()
    rows = list(session.exec(select(AssetRecord)).all())
    by_status: dict[str, int] = {}
    by_category: dict[str, int] = {}
    installed_value = 0.0
    installed_count = 0
    in_warranty = 0
    expiring = 0
    for a in rows:
        by_status[a.status] = by_status.get(a.status, 0) + 1
        by_category[a.category] = by_category.get(a.category, 0) + 1
        if a.status == 'installed':
            installed_count += 1
            installed_value += a.purchase_cost
            if a.warranty_until and a.warranty_until >= today:
                in_warranty += 1
                if (a.warranty_until - today).days <= soon_days:
                    expiring += 1
    return AssetSummary(
        total=len(rows),
        by_status=by_status,
        by_category=by_category,
        installed_count=installed_count,
        installed_base_value=installed_value,
        in_warranty=in_warranty,
        warranty_expiring_soon=expiring,
    )
