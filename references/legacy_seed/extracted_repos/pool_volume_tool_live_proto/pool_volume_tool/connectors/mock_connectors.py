from __future__ import annotations

from typing import Any

from .base import ImageryConnector, PermitConnector


MOCK_PERMITS: dict[str, list[dict[str, Any]]] = {
    "demo-public-pool": [
        {
            "permit_id": "PUB-1001",
            "source": "mock_permit_portal",
            "water_surface_area_sqft": 1820,
            "shallow_depth_ft": 3.5,
            "deep_depth_ft": 8.0,
            "pool_type": "public",
            "design_volume_gallons": 78350,
            "notes": "DOH plan sheet lists surface area and design volume.",
        }
    ],
    "demo-resort-pool": [
        {
            "permit_id": "COM-2210",
            "source": "mock_permit_portal",
            "water_surface_area_sqft": 1450,
            "shallow_depth_ft": 3.5,
            "deep_depth_ft": 6.0,
            "pool_type": "commercial",
            "notes": "Permit notes show dimensions and sloped floor but no explicit gallons.",
        }
    ],
}

MOCK_IMAGERY: dict[str, list[dict[str, Any]]] = {
    "demo-public-pool": [
        {
            "source": "mock_imagery",
            "measured_surface_area_sqft": 1808,
            "shape": "rectangle",
            "confidence": 0.96,
        }
    ],
    "demo-resort-pool": [
        {
            "source": "mock_imagery",
            "measured_surface_area_sqft": 1472,
            "shape": "freeform",
            "confidence": 0.92,
        }
    ],
    "demo-backyard-pool": [
        {
            "source": "mock_imagery",
            "measured_surface_area_sqft": 512,
            "shape": "freeform",
            "confidence": 0.87,
        }
    ],
}


class MockPermitConnector(PermitConnector):
    def fetch(self, address: str | None, parcel_id: str | None) -> list[dict[str, Any]]:
        key = (parcel_id or address or "").strip().lower()
        return MOCK_PERMITS.get(key, [])


class MockImageryConnector(ImageryConnector):
    def fetch(self, address: str | None, parcel_id: str | None) -> list[dict[str, Any]]:
        key = (parcel_id or address or "").strip().lower()
        return MOCK_IMAGERY.get(key, [])
