from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(slots=True)
class FreshBooksConnectionStatus:
    api_base_url: str
    auth_mode: str
    has_access_token: bool
    has_account_id: bool
    configured: bool
    live_write_enabled: bool
    sync_mode: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class FreshBooksSyncOperation:
    method: str
    path: str
    summary: str
    payload: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class FreshBooksSyncResult:
    mode: str
    sync_status: str
    message: str
    operations: list[FreshBooksSyncOperation] = field(default_factory=list)
    external_links: list[dict[str, Any]] = field(default_factory=list)
    quote_case: dict[str, Any] | None = None
    freshbooks_summary: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload['operations'] = [operation.to_dict() for operation in self.operations]
        return payload
