from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class ExpectationProfile(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    entity_type: str = Field(index=True)
    entity_ref: str = Field(index=True)
    model_family: str = Field(index=True)
    payload_json: str = '{}'
    created_at: datetime = Field(default_factory=datetime.utcnow)


class VarianceFact(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    entity_type: str = Field(index=True)
    entity_ref: str = Field(index=True)
    metric_name: str = Field(index=True)
    expected_value: float = 0.0
    actual_value: float = 0.0
    variance_value: float = 0.0
    variance_pct: float = 0.0
    created_at: datetime = Field(default_factory=datetime.utcnow)


class DriverAttributionFact(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    variance_fact_id: int = Field(index=True)
    driver_name: str = Field(index=True)
    driver_weight: float = 0.0
    notes: str = ''


class CalibrationSuggestion(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    entity_type: str = Field(index=True)
    entity_ref: str = Field(index=True)
    suggestion_type: str = Field(index=True)
    payload_json: str = '{}'
    status: str = Field(default='suggested', index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ProfitabilitySignal(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    entity_type: str = Field(index=True)
    entity_ref: str = Field(index=True)
    gross_margin_pct: float = 0.0
    signal: str = Field(default='neutral', index=True)
    notes: str = ''
    created_at: datetime = Field(default_factory=datetime.utcnow)


class BranchOverlay(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    branch_slug: str = Field(index=True, unique=True)
    climate_profile_override_id: Optional[int] = Field(default=None, index=True)
    labor_multiplier: float = 1.0
    chemical_multiplier: float = 1.0
    pricing_multiplier: float = 1.0
    notes: str = ''
    created_at: datetime = Field(default_factory=datetime.utcnow)
