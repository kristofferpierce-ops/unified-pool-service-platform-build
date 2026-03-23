from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class ManualOverrides(BaseModel):
    shallow_depth_ft: float | None = Field(default=None, ge=0)
    deep_depth_ft: float | None = Field(default=None, ge=0)
    avg_depth_ft: float | None = Field(default=None, ge=0)
    attached_spa_gallons: float | None = Field(default=None, ge=0)
    property_type: Literal["residential", "commercial", "public", "unknown"] | None = None


class EstimateRequest(BaseModel):
    address: str | None = None
    parcel_id: str | None = None
    permit_records: list[dict[str, Any]] = Field(default_factory=list)
    imagery_measurements: list[dict[str, Any]] = Field(default_factory=list)
    manual_overrides: ManualOverrides | None = None
    use_live_sources: bool = True


class EvidenceItem(BaseModel):
    source: str
    evidence_type: str
    summary: str
    raw: dict[str, Any] = Field(default_factory=dict)


class EstimateResult(BaseModel):
    gallons_estimate: float
    gallons_low: float
    gallons_high: float
    confidence: Literal["high", "medium", "low"]
    method: str
    average_depth_ft: float
    surface_area_sqft: float | None = None
    evidence: list[EvidenceItem] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)


class HealthResponse(BaseModel):
    ok: bool = True
    service: str = "pool-volume-tool"
