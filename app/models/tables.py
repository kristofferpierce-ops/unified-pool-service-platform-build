from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class ExpenseItem(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    category: str
    name: str
    annual_cost: float = 0.0
    notes: str = ""


class ChemicalProduct(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    sku: str = Field(index=True, unique=True)
    name: str
    unit: str
    default_unit_cost: float = 0.0
    manufacturer: str = ""
    manufacturer_part_number: str = Field(default="", index=True)
    default_vendor: str = ""
    aliases_csv: str = ""
    product_family: str = "chemical"
    is_active: bool = True


class ProductPriceHistory(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    product_id: int = Field(index=True)
    vendor_name: str = ""
    invoice_number: str = ""
    effective_date: date = Field(default_factory=date.today)
    unit_cost: float = 0.0
    pack_size: str = ""
    confidence: float = 0.0
    approved_by: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ClimateProfile(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True, unique=True)
    location: str
    monthly_temperature_csv: str
    monthly_rainfall_csv: str
    monthly_uv_csv: str
    source_notes: str = ""


class WaterProfile(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True, unique=True)
    source_system: str = ""
    ph: float = 7.5
    total_alkalinity_ppm: float = 0.0
    calcium_hardness_ppm: float = 0.0
    tds_ppm: float = 0.0
    chloride_ppm: float = 0.0
    sodium_ppm: float = 0.0
    notes: str = ""


class BaselineModelVersion(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    model_family: str = Field(index=True)
    version_name: str = Field(index=True)
    description: str = ""
    climate_profile_id: int = Field(index=True)
    water_profile_id: int = Field(index=True)
    coefficients_json: str = ""
    weights_json: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)
    is_active: bool = True


class Account(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    account_type: str = Field(index=True)
    name: str = Field(index=True)
    billing_name: str = ""
    notes: str = ""


class Property(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    account_id: int = Field(index=True)
    name: str
    address_line_1: str = ""
    city: str = ""
    state: str = ""
    postal_code: str = ""
    latitude: float = 0.0
    longitude: float = 0.0
    drive_minutes_round_trip: float = 0.0
    account_type: str = Field(index=True)


class PoolVessel(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    property_id: int = Field(index=True)
    name: str
    gallons: float = 0.0
    surface_type: str = ""
    covered: bool = False
    indoor: bool = False
    heated: bool = False
    service_frequency_per_month: float = 4.0
    training_weeks_per_year: int = 0
    bathing_score: int = 5
    debris_score: int = 5
    filtration_score: int = 5
    overflow_score: int = 5
    backwash_score: int = 5
    minutes_on_site: float = 25.0


class EquipmentAsset(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    vessel_id: int = Field(index=True)
    asset_type: str
    manufacturer: str = ""
    model_number: str = ""
    part_number: str = ""
    reference_tag: str = ""
    notes: str = ""


class EstimateScenario(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    property_id: int = Field(index=True)
    vessel_id: Optional[int] = Field(default=None, index=True)
    scenario_name: str
    model_family: str = Field(index=True)
    baseline_model_version_id: int = Field(index=True)
    target_margin_pct: float = 35.0
    global_adjustment_pct: float = 0.0
    notes: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)


class EstimateRun(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    scenario_id: int = Field(index=True)
    property_id: int = Field(index=True)
    vessel_id: Optional[int] = Field(default=None, index=True)
    run_timestamp: datetime = Field(default_factory=datetime.utcnow)
    input_snapshot_json: str = ""
    output_snapshot_json: str = ""
    monthly_real_cost: float = 0.0
    monthly_sell_price: float = 0.0
    annual_real_cost: float = 0.0


class WaterTestLog(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    property_id: int = Field(index=True)
    vessel_id: Optional[int] = Field(default=None, index=True)
    logged_at: datetime = Field(default_factory=datetime.utcnow)
    free_chlorine_ppm: float = 0.0
    ph: float = 0.0
    total_alkalinity_ppm: float = 0.0
    calcium_hardness_ppm: float = 0.0
    cya_ppm: float = 0.0
    phosphates_ppb: float = 0.0
    notes: str = ""


class ChemicalUsageLog(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    property_id: int = Field(index=True)
    vessel_id: Optional[int] = Field(default=None, index=True)
    logged_at: datetime = Field(default_factory=datetime.utcnow)
    chemical_product_id: Optional[int] = Field(default=None, index=True)
    chemical_name: str
    quantity: float = 0.0
    unit: str
    source: str = "manual"
    notes: str = ""


class ServiceLog(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    property_id: int = Field(index=True)
    vessel_id: Optional[int] = Field(default=None, index=True)
    logged_at: datetime = Field(default_factory=datetime.utcnow)
    minutes_on_site_actual: float = 0.0
    drive_minutes_actual: float = 0.0
    tech_count: int = 1
    notes: str = ""


class CalibrationAdjustment(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    model_family: str = Field(index=True)
    property_id: Optional[int] = Field(default=None, index=True)
    vessel_id: Optional[int] = Field(default=None, index=True)
    chemical_name: str = ""
    labor_multiplier: float = 1.0
    chemical_multiplier: float = 1.0
    source: str = "manual"
    notes: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)


class CommercialVendorOrder(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    property_id: int = Field(index=True)
    vendor_name: str = Field(index=True)
    order_number: str = Field(index=True)
    ordered_at: datetime = Field(default_factory=datetime.utcnow)
    status: str = "ordered"
    notes: str = ""


class CommercialVendorOrderItem(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    order_id: int = Field(index=True)
    product_id: Optional[int] = Field(default=None, index=True)
    product_name: str
    quantity_ordered: float = 0.0
    unit: str
    unit_cost: float = 0.0
    expected_total: float = 0.0


class CommercialDelivery(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    property_id: int = Field(index=True)
    vendor_name: str = Field(index=True)
    invoice_number: str = Field(index=True)
    delivery_ticket: str = ""
    delivered_at: datetime = Field(default_factory=datetime.utcnow)
    status: str = "delivered"
    source_document_id: Optional[int] = Field(default=None, index=True)
    notes: str = ""


class CommercialDeliveryItem(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    delivery_id: int = Field(index=True)
    order_item_id: Optional[int] = Field(default=None, index=True)
    product_id: Optional[int] = Field(default=None, index=True)
    product_name: str
    quantity_ordered: float = 0.0
    quantity_delivered: float = 0.0
    quantity_confirmed: float = 0.0
    unit: str
    unit_cost: float = 0.0
    confidence: float = 0.0


class InventorySnapshot(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    property_id: int = Field(index=True)
    vessel_id: Optional[int] = Field(default=None, index=True)
    product_id: Optional[int] = Field(default=None, index=True)
    product_name: str
    on_hand_quantity: float = 0.0
    unit: str
    snapshot_at: datetime = Field(default_factory=datetime.utcnow)
    notes: str = ""


class InvoiceDocument(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    vendor_name: str = Field(default="", index=True)
    original_filename: str
    file_path: str
    document_hash: str = ""
    invoice_number: str = Field(default="", index=True)
    extracted_text: str = ""
    parser_name: str = "heuristic_pdf_parser"
    status: str = "staged"
    created_at: datetime = Field(default_factory=datetime.utcnow)


class InvoiceLineStaging(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    document_id: int = Field(index=True)
    raw_line_text: str
    product_text: str = ""
    matched_product_id: Optional[int] = Field(default=None, index=True)
    matched_property_id: Optional[int] = Field(default=None, index=True)
    matched_order_item_id: Optional[int] = Field(default=None, index=True)
    manufacturer_part_number: str = ""
    vendor_sku: str = ""
    quantity: float = 0.0
    unit: str = ""
    unit_cost: float = 0.0
    confidence: float = 0.0
    bucket: str = "exception"
    review_status: str = "pending"
    suggestion_json: str = ""


class SupplierTrainingExample(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    vendor_name: str = Field(index=True)
    source_document_id: Optional[int] = Field(default=None, index=True)
    raw_text: str
    approved_product_id: Optional[int] = Field(default=None, index=True)
    approved_property_id: Optional[int] = Field(default=None, index=True)
    correction_notes: str = ""
    outcome: str = "approved"
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ToolCatalogEntry(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    slug: str = Field(index=True, unique=True)
    name: str
    category: str = Field(index=True)
    description: str = ""
    page_key: str = ""
    is_enabled: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ToolRun(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    tool_slug: str = Field(index=True)
    status: str = "completed"
    input_json: str = ""
    output_json: str = ""
    notes: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ApprovedAgent(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    property_id: int = Field(index=True)
    full_name: str = Field(index=True)
    role_label: str = ""
    company_name: str = ""
    phone: str = ""
    email: str = ""
    approval_source: str = "manual"
    notes: str = ""
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)


class PropertyVerificationCase(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    property_id: Optional[int] = Field(default=None, index=True)
    tool_run_id: Optional[int] = Field(default=None, index=True)
    account_type: str = Field(default="residential", index=True)
    input_address: str = Field(index=True)
    caller_name: str = Field(index=True)
    caller_phone: str = ""
    caller_role: str = ""
    parcel_id: str = Field(default="", index=True)
    owner_name: str = Field(default="", index=True)
    owner_mailing_address: str = ""
    owner_type: str = "unknown"
    sunbiz_entity_name: str = ""
    sunbiz_role_matches: str = ""
    approved_agent_matches: str = ""
    verification_status: str = Field(default="needs_owner_approval", index=True)
    recommended_action: str = ""
    source_mode: str = "manual"
    raw_payload_json: str = ""
    notes: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)
