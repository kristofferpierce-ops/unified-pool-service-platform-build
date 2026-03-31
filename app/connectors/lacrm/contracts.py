from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(slots=True)
class LACRMConnectionStatus:
    api_base_url: str
    has_api_key: bool
    configured: bool
    live_write_enabled: bool
    sync_mode: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class LACRMSyncOperation:
    function: str
    parameters: dict[str, Any]
    summary: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class LACRMSyncResult:
    mode: str
    sync_status: str
    message: str
    operations: list[LACRMSyncOperation] = field(default_factory=list)
    external_links: list[dict[str, Any]] = field(default_factory=list)
    quote_case: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload['operations'] = [operation.to_dict() for operation in self.operations]
        return payload
