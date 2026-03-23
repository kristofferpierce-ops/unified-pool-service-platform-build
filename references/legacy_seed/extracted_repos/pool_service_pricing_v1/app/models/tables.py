from __future__ import annotations

from datetime import date, datetime
from typing import Any, Optional

from sqlalchemy import Column, JSON, Text
from sqlmodel import Field, SQLModel


class SystemSetting(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    key: str = Field(index=True, unique=True)
    value: Any = Field(default=None, sa_column=Column(JSON))
    description: str = Field(default="")


class CompanyExpense(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    category: str = Field(index=True)
    expense_name: str = Field(index=True)
    annual_cost: float = Field(default=0.0)
    notes: str = Field(default="")


class ChemicalCatalog(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    key: str = Field(index=True, unique=True)
    display_name: str
    unit_name: str
    default_unit_cost: float = Field(default=0.0)
    active: bool = Field(default=True)


class WaterProfile(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True, unique=True)
    source_name: str = Field(default="")
    ph: float = Field(default=7.5)
    total_alkalinity_ppm: float = Field(default=80.0)
    calcium_hardness_ppm: float = Field(default=200.0)
    tds_ppm: float = Field(default=500.0)
    chloride_ppm: float = Field(default=0.0)
    sodium_ppm: float = Field(default=0.0)
    notes: str = Field(default="")


class ClimateProfile(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True, unique=True)
    location_name: str = Field(default="")
    avg_annual_rain_inches: float = Field(default=0.0)
    avg_uv_index: float = Field(default=0.0)
    avg_air_temp_f: float = Field(default=0.0)
    notes: str = Field(default="")


class BaselineModelVersion(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True, unique=True)
    description: str = Field(default="")
    pool_type: str = Field(default="residential", index=True)
    active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    climate_profile_id: Optional[int] = Field(default=None, index=True)
    water_profile_id: Optional[int] = Field(default=None, index=True)


class ChemicalCoefficient(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    model_version_id: int = Field(index=True)
    chemical_key: str = Field(index=True)
    annual_coefficient_per_pool_gallon: float = Field(default=0.0)


class ChemicalWeight(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    model_version_id: int = Field(index=True)
    chemical_key: str = Field(index=True)
    bath_weight: float = Field(default=0.0)
    debris_weight: float = Field(default=0.0)
    filtration_weight: float = Field(default=0.0)
    overflow_weight: float = Field(default=0.0)
    backwash_weight: float = Field(default=0.0)


class Property(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    property_name: str = Field(index=True)
    address_line_1: str = Field(default="")
    city: str = Field(default="")
    state: str = Field(default="")
    postal_code: str = Field(default="")
    pool_type: str = Field(default="residential", index=True)
    pool_gallons: float = Field(default=15000.0)
    covered_most_of_time: bool = Field(default=False)
    visits_per_month: float = Field(default=4.0)
    minutes_on_site: float = Field(default=25.0)
    drive_minutes_round_trip: float = Field(default=20.0)
    notes: str = Field(default="")
    active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class EstimateRun(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    property_id: int = Field(index=True)
    model_version_id: int = Field(index=True)
    scenario_name: str = Field(default="Baseline")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    input_snapshot: Any = Field(default=None, sa_column=Column(JSON))
    output_snapshot: Any = Field(default=None, sa_column=Column(JSON))
    notes: str = Field(default="")


class FieldObservation(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    property_id: int = Field(index=True)
    estimate_run_id: Optional[int] = Field(default=None, index=True)
    observed_on: date = Field(default_factory=date.today, index=True)
    actual_site_minutes: float = Field(default=0.0)
    actual_drive_minutes_round_trip: float = Field(default=0.0)
    actual_chemical_usage: Any = Field(default=None, sa_column=Column(JSON))
    actual_test_data: Any = Field(default=None, sa_column=Column(JSON))
    notes: str = Field(default="")
    created_at: datetime = Field(default_factory=datetime.utcnow)
