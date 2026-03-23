from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class BillingDocument(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    source_slug: str = Field(default='freshbooks', index=True)
    external_id: str = Field(default='', index=True)
    account_id: Optional[int] = Field(default=None, index=True)
    issued_on: Optional[date] = None
    total_amount: float = 0.0
    status: str = Field(default='draft', index=True)
    raw_json: str = '{}'
    created_at: datetime = Field(default_factory=datetime.utcnow)


class BillingLine(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    billing_document_id: int = Field(index=True)
    description: str
    quantity: float = 0.0
    unit_price: float = 0.0
    amount: float = 0.0


class PaymentEvent(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    billing_document_id: int = Field(index=True)
    paid_at: Optional[datetime] = None
    amount: float = 0.0
    source_slug: str = Field(default='freshbooks', index=True)
    external_id: str = Field(default='', index=True)


class ReconciliationFact(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    property_id: Optional[int] = Field(default=None, index=True)
    expectation_ref: str = ''
    billing_document_id: Optional[int] = Field(default=None, index=True)
    expected_amount: float = 0.0
    billed_amount: float = 0.0
    paid_amount: float = 0.0
    variance_amount: float = 0.0
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ServiceVisit(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    property_id: int = Field(index=True)
    vessel_id: Optional[int] = Field(default=None, index=True)
    occurred_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    source_slug: str = Field(default='skimmer', index=True)
    external_id: str = Field(default='', index=True)
    status: str = Field(default='completed', index=True)
    notes: str = ''


class TechnicianAssignment(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    service_visit_id: int = Field(index=True)
    technician_name: str = Field(index=True)
    assigned_minutes: float = 0.0


class FieldObservation(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    service_visit_id: int = Field(index=True)
    observation_type: str = Field(index=True)
    value_json: str = '{}'
    notes: str = ''


class ActualLaborFact(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    service_visit_id: int = Field(index=True)
    total_minutes: float = 0.0
    drive_minutes: float = 0.0
    tech_count: int = 1


class ActualChemicalFact(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    service_visit_id: int = Field(index=True)
    chemical_product_id: Optional[int] = Field(default=None, index=True)
    chemical_name: str
    quantity: float = 0.0
    unit: str = ''
