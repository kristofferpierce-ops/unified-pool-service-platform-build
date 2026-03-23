from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class PermitConnector(ABC):
    @abstractmethod
    def fetch(self, address: str | None, parcel_id: str | None) -> list[dict[str, Any]]:
        raise NotImplementedError


class ImageryConnector(ABC):
    @abstractmethod
    def fetch(self, address: str | None, parcel_id: str | None) -> list[dict[str, Any]]:
        raise NotImplementedError
