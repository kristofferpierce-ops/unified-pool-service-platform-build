from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class HeaterQuoteRun(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    quote_case_id: Optional[int] = Field(default=None, index=True)
    title: str = Field(default='', index=True)
    shape: str = Field(default='direct')
    heater_kind_preference: str = Field(default='auto', index=True)
    fuel_preference: str = Field(default='auto', index=True)
    volume_gallons: float = 0.0
    surface_area_sqft: float = 0.0
    current_water_temp_f: float = 0.0
    target_water_temp_f: float = 0.0
    ambient_air_temp_f: float = 0.0
    desired_heatup_hours: float = 24.0
    wind_mph: float = 0.0
    covered: bool = False
    total_btu_required: float = 0.0
    maintenance_btu_per_hr: float = 0.0
    heatup_btu_per_hr: float = 0.0
    recommended_btu_per_hr: float = 0.0
    source_mode: str = Field(default='no_catalog', index=True)
    summary_json: str = '{}'
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class HeaterQuoteCandidate(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    run_id: int = Field(index=True)
    rank_order: int = Field(default=0, index=True)
    recommendation_band: str = Field(default='review', index=True)
    vendor_name: str = Field(default='')
    brand_name: str = Field(default='')
    model_name: str = Field(default='', index=True)
    sku: str = Field(default='', index=True)
    heater_kind: str = Field(default='', index=True)
    fuel_type: str = Field(default='', index=True)
    capacity_btu_per_hr: float = 0.0
    estimated_heatup_hours: float = 0.0
    price: Optional[float] = Field(default=None, index=True)
    currency_code: str = Field(default='USD')
    availability_status: str = Field(default='')
    branch_name: str = Field(default='')
    fit_score: float = 0.0
    payload_json: str = '{}'
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)
