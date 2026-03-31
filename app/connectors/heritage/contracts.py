from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(slots=True)
class HeritageConnectionStatus:
    catalog_url: str
    local_catalog_path: str
    auth_mode: str
    has_account_id: bool
    has_api_key: bool
    has_branch_id: bool
    has_catalog_source: bool
    configured: bool
    live_catalog_enabled: bool
    sync_mode: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class HeritageCatalogItem:
    sku: str
    model_name: str
    brand_name: str = ''
    heater_kind: str = ''
    fuel_type: str = ''
    capacity_btu_per_hr: float = 0.0
    price: float | None = None
    currency_code: str = 'USD'
    availability_status: str = ''
    branch_name: str = ''
    payload: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
