# Code excerpt library

Each section below includes the file path, why it matters, and a short excerpt. Full file copies are in the annex.


## `/mnt/data/_extracted/pool_service_platform_v3/pool_service_platform_v3/pool_service_platform_v3/app/models/tables.py`
Why it matters: platform_v3 core model backbone


### ExpenseItem
```python
class ExpenseItem(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    category: str
    name: str
    annual_cost: float = 0.0
    notes: str = ""
```


### ChemicalProduct
```python
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
```


### ProductPriceHistory
```python
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
```


### ClimateProfile
```python
class ClimateProfile(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True, unique=True)
    location: str
    monthly_temperature_csv: str
    monthly_rainfall_csv: str
    monthly_uv_csv: str
    source_notes: str = ""
```


### WaterProfile
```python
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
```


### BaselineModelVersion
```python
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
```


### Account
```python
class Account(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    account_type: str = Field(index=True)
    name: str = Field(index=True)
    billing_name: str = ""
    notes: str = ""
```


### Property
```python
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
```


### PoolVessel
```python
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
```


### CommercialVendorOrder
```python
class CommercialVendorOrder(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    property_id: int = Field(index=True)
    vendor_name: str = Field(index=True)
    order_number: str = Field(index=True)
    ordered_at: datetime = Field(default_factory=datetime.utcnow)
    status: str = "ordered"
    notes: str = ""
```


### InvoiceDocument
```python
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
```


### ToolCatalogEntry
```python
class ToolCatalogEntry(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    slug: str = Field(index=True, unique=True)
    name: str
    category: str = Field(index=True)
    description: str = ""
    page_key: str = ""
    is_enabled: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
```


### PropertyVerificationCase
```python
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
```


## `/mnt/data/_extracted/pool_service_platform_v3/pool_service_platform_v3/pool_service_platform_v3/app/services/invoice_ingestion.py`
Why it matters: platform_v3 staging and approve-apply pattern


### ingest_invoice_document
```python
def ingest_invoice_document(session: Session, file_path: str | Path, vendor_name: str = "") -> InvoiceDocument:
    file_path = Path(file_path)
    destination = UPLOAD_DIR / file_path.name
    if file_path.resolve() != destination.resolve():
        destination.write_bytes(file_path.read_bytes())
    raw = destination.read_bytes()
    document_hash = hashlib.sha256(raw).hexdigest()
    extracted_text = _extract_text(destination)
    invoice_number_match = INVOICE_RE.search(extracted_text)
    invoice_number = invoice_number_match.group(1) if invoice_number_match else ""
    document = InvoiceDocument(
        vendor_name=vendor_name,
        original_filename=destination.name,
        file_path=str(destination),
        document_hash=document_hash,
        invoice_number=invoice_number,
        extracted_text=extracted_text,
        status="staged",
    )
    session.add(document)
    session.commit()
    session.refresh(document)
    stage_invoice_lines(session, document.id)
    return document
```


### stage_invoice_lines
```python
def stage_invoice_lines(session: Session, document_id: int) -> list[InvoiceLineStaging]:
    document = session.get(InvoiceDocument, document_id)
    if not document:
        raise ValueError("Document not found")
    product_candidates = _product_candidates(session)
    property_candidates = _property_candidates(session)
    created = []
    for raw_line in document.extracted_text.splitlines():
        line = raw_line.strip()
        if not line or len(line) < 6:
            continue
        match = LINE_RE.search(line)
        quantity = float(match.group("qty")) if match else 0.0
        unit = (match.group("unit") if match else "") or ""
        product_text = (match.group("desc") if match else line).strip()
        unit_cost = float(match.group("cost")) if match else 0.0

        product_id, product_score, product_suggestions = best_match(product_text, product_candidates)
        property_id, property_score, property_suggestions = best_match(document.extracted_text[:500], property_candidates)

        confidence = max(product_score, 0.0)
        if product_score >= 0.95:
            bucket = "high_confidence"
        elif product_score >= 0.75:
            bucket = "assisted_match"
        else:
            bucket = "exception"

        staged = InvoiceLineStaging(
            document_id=document_id,
            raw_line_text=line,
            product_text=product_text,
            matched_product_id=product_id,
            matched_property_id=property_id if property_score >= 0.55 else None,
            quantity=quantity,
            unit=unit,
```


### approve_staged_line
```python
def approve_staged_line(session: Session, staging_id: int, approved_by: str = "ui") -> InvoiceLineStaging:
    line = session.get(InvoiceLineStaging, staging_id)
    if not line:
        raise ValueError("Staged line not found")
    document = session.get(InvoiceDocument, line.document_id)
    if line.matched_product_id and line.unit_cost > 0:
        create_price_history(
            session,
            product_id=line.matched_product_id,
            vendor_name=document.vendor_name if document else "",
            invoice_number=document.invoice_number if document else "",
            unit_cost=line.unit_cost,
            pack_size=line.unit,
            confidence=line.confidence,
            approved_by=approved_by,
        )
    if line.matched_property_id:
        delivery = create_delivery(
            session,
            property_id=line.matched_property_id,
            vendor_name=document.vendor_name if document else "",
            invoice_number=document.invoice_number if document else "",
            delivery_ticket=document.original_filename if document else "",
            status="delivered",
            source_document_id=document.id if document else None,
        )
        add_delivery_item(
            session,
            delivery_id=delivery.id,
            product_name=line.product_text,
            quantity_ordered=line.quantity,
            quantity_delivered=line.quantity,
            quantity_confirmed=0.0,
            unit=line.unit or "ea",
            unit_cost=line.unit_cost,
            product_id=line.matched_product_id,
```


## `/mnt/data/_extracted/pool_service_platform_v3/pool_service_platform_v3/pool_service_platform_v3/app/services/estimator.py`
Why it matters: platform_v3 estimating core


### LaborSettings
```python
class LaborSettings:
    tech_hourly_wage: float = 22.0
    payroll_tax_burden_pct: float = 10.0
    benefits_burden_pct: float = 5.0
    billable_hours_per_tech_per_year: float = 1500.0
    number_of_route_techs: int = 4
```


### EstimateInput
```python
class EstimateInput:
    property_id: int
    vessel_id: int | None
    model_family: str
    gallons: float
    visits_per_month: float
    minutes_on_site: float
    drive_minutes_round_trip: float
    techs_on_visit: int
    bath_score: int
    debris_score: int
    filtration_score: int
    overflow_score: int
    backwash_score: int
    target_margin_pct: float
    global_adjustment_pct: float = 0.0
```


### EstimateOutput
```python
class EstimateOutput:
    chemical_quantities: dict
    chemical_costs: dict
    service_costs: dict
    monthly_real_cost: float
    annual_real_cost: float
    monthly_sell_price: float
    annual_sell_price: float
    visit_sell_price: float
```


### calculate_estimate
```python
def calculate_estimate(session: Session, estimate_input: EstimateInput, labor_settings: LaborSettings | None = None) -> EstimateOutput:
    labor_settings = labor_settings or LaborSettings()
    baseline_model = get_active_model(session, estimate_input.model_family)
    model_payload = load_model_payload(baseline_model)
    calibration = account_calibration_map(session, estimate_input.property_id)

    chemical_quantities = estimate_chemical_quantities(
        gallons=estimate_input.gallons,
        model_payload=model_payload,
        bath_score=estimate_input.bath_score,
        debris_score=estimate_input.debris_score,
        filtration_score=estimate_input.filtration_score,
        overflow_score=estimate_input.overflow_score,
        backwash_score=estimate_input.backwash_score,
        global_adjustment_pct=estimate_input.global_adjustment_pct,
        calibration=calibration,
    )

    products = {product.sku.lower().replace("-", "_"): product for product in session.exec(select(ChemicalProduct).where(ChemicalProduct.is_active == True)).all()}
    alias_map = {
        "liquid_chlorine_12pct_gal": "liq_cl_12",
        "muriatic_acid_gal": "muri_acid",
        "sodium_bicarbonate_lb": "sod_bicarb",
        "cyanuric_acid_lb": "cya_gran",
        "calcium_chloride_lb": "cal_chl",
        "algaecide_oz": "algae_poly",
        "phosphate_remover_oz": "phos_rem",
    }

    chemical_costs = {}
    monthly_chemical_cost = 0.0
    annual_chemical_cost = 0.0
    for chemical_name, values in chemical_quantities.items():
        lookup_key = alias_map.get(chemical_name, chemical_name)
        product = products.get(lookup_key)
        unit_cost = latest_unit_cost(session, product) if product else 0.0
```


### save_estimate_run
```python
def save_estimate_run(session: Session, scenario_id: int, estimate_input: EstimateInput, estimate_output: EstimateOutput) -> EstimateRun:
    record = EstimateRun(
        scenario_id=scenario_id,
        property_id=estimate_input.property_id,
        vessel_id=estimate_input.vessel_id,
        input_snapshot_json=dumps(asdict(estimate_input)),
        output_snapshot_json=dumps(asdict(estimate_output)),
        monthly_real_cost=estimate_output.monthly_real_cost,
        monthly_sell_price=estimate_output.monthly_sell_price,
        annual_real_cost=estimate_output.annual_real_cost,
    )
    session.add(record)
    session.commit()
    session.refresh(record)
    return record
```


## `/mnt/data/_extracted/pool_service_platform_v3/pool_service_platform_v3/pool_service_platform_v3/app/services/baseline.py`
Why it matters: platform_v3 deterministic chemistry logic


### get_active_model
```python
def get_active_model(session: Session, model_family: str) -> BaselineModelVersion:
    model = session.exec(
        select(BaselineModelVersion)
        .where(BaselineModelVersion.model_family == model_family, BaselineModelVersion.is_active == True)
        .order_by(BaselineModelVersion.id.desc())
    ).first()
    if not model:
        raise ValueError(f"No active baseline model found for {model_family}")
    return model
```


### build_condition_multiplier
```python
def build_condition_multiplier(weights: dict[str, float], *, bath_score: int, debris_score: int,
                               filtration_score: int, overflow_score: int, backwash_score: int) -> float:
    pressures = {
        "bath": score_to_pressure(bath_score),
        "debris": score_to_pressure(debris_score),
        "filtration": score_to_pressure(filtration_score),
        "overflow": score_to_pressure(overflow_score),
        "backwash": score_to_pressure(backwash_score),
    }
    weighted = sum(pressures[key] * weights.get(key, 0.0) for key in pressures)
    return max(0.30, 1.0 + weighted)
```


### estimate_chemical_quantities
```python
def estimate_chemical_quantities(*, gallons: float, model_payload: dict[str, Any], bath_score: int, debris_score: int,
                                 filtration_score: int, overflow_score: int, backwash_score: int,
                                 global_adjustment_pct: float, calibration: dict[str, float] | None = None) -> dict[str, dict[str, float]]:
    coefficients = model_payload["coefficients"]
    weights = model_payload["weights"]
    calibration = calibration or {}
    global_factor = 1.0 + (global_adjustment_pct / 100.0)
    output: dict[str, dict[str, float]] = {}
    for chemical, coefficient in coefficients.items():
        chemical_weights = weights.get(chemical, {})
        multiplier = build_condition_multiplier(
            chemical_weights,
            bath_score=bath_score,
            debris_score=debris_score,
            filtration_score=filtration_score,
            overflow_score=overflow_score,
            backwash_score=backwash_score,
        )
        calibration_factor = calibration.get(chemical, 1.0)
        annual_quantity = gallons * coefficient * multiplier * global_factor * calibration_factor
        output[chemical] = {
            "base_coefficient": coefficient,
            "condition_multiplier": multiplier,
            "calibration_factor": calibration_factor,
            "annual_quantity": annual_quantity,
            "monthly_quantity": annual_quantity / 12.0,
            "effective_coefficient": annual_quantity / gallons if gallons else 0.0,
        }
    return output
```


## `/mnt/data/_extracted/pool_service_platform_v3/pool_service_platform_v3/pool_service_platform_v3/app/services/calibration.py`
Why it matters: platform_v3 expected versus actual pattern


### compare_estimate_to_actual
```python
def compare_estimate_to_actual(session: Session, property_id: int, vessel_id: int | None = None) -> dict:
    estimate = session.exec(
        select(EstimateRun).where(EstimateRun.property_id == property_id).order_by(EstimateRun.run_timestamp.desc())
    ).first()
    if not estimate:
        return {"estimate_found": False, "chemical_variance": [], "labor_variance": {}}

    output = loads(estimate.output_snapshot_json, {})
    predicted_chemicals = output.get("chemical_quantities", {})
    actual_chemicals = defaultdict(float)
    chemical_logs = session.exec(select(ChemicalUsageLog).where(ChemicalUsageLog.property_id == property_id)).all()
    for log in chemical_logs:
        actual_chemicals[log.chemical_name] += log.quantity

    rows = []
    for chemical, predicted in predicted_chemicals.items():
        predicted_annual = predicted.get("annual_quantity", 0.0)
        actual = actual_chemicals.get(chemical, 0.0)
        variance = actual - predicted_annual
        variance_pct = (variance / predicted_annual * 100.0) if predicted_annual else 0.0
        suggested_multiplier = (actual / predicted_annual) if predicted_annual and actual > 0 else 1.0
        rows.append({
            "chemical": chemical,
            "predicted_annual": predicted_annual,
            "actual_logged": actual,
            "variance": variance,
            "variance_pct": variance_pct,
            "suggested_multiplier": suggested_multiplier,
        })

    predicted_service = output.get("service_costs", {})
    predicted_minutes = predicted_service.get("adjusted_site_minutes", 0.0) + predicted_service.get("adjusted_drive_minutes", 0.0)
    service_logs = list(session.exec(select(ServiceLog).where(ServiceLog.property_id == property_id)).all())
    actual_minutes = sum(log.minutes_on_site_actual + log.drive_minutes_actual for log in service_logs)
    actual_visits = max(1, len(service_logs))
    avg_actual_minutes = actual_minutes / actual_visits if service_logs else 0.0
```


### save_suggested_calibration
```python
def save_suggested_calibration(session: Session, model_family: str, property_id: int | None, vessel_id: int | None,
                              chemical_name: str, chemical_multiplier: float, labor_multiplier: float = 1.0,
                              notes: str = "") -> CalibrationAdjustment:
    adjustment = CalibrationAdjustment(
        model_family=model_family,
        property_id=property_id,
        vessel_id=vessel_id,
        chemical_name=chemical_name,
        chemical_multiplier=chemical_multiplier,
        labor_multiplier=labor_multiplier,
        source="suggested",
        notes=notes,
    )
    session.add(adjustment)
    session.commit()
    session.refresh(adjustment)
    return adjustment
```


## `/mnt/data/_extracted/pool_service_pricing_v1/pool_service_pricing_v1/pool_service_pricing_v1/app/models/tables.py`
Why it matters: pricing_v1 concepts worth mining


### SystemSetting
```python
class SystemSetting(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    key: str = Field(index=True, unique=True)
    value: Any = Field(default=None, sa_column=Column(JSON))
    description: str = Field(default="")
```


### BaselineModelVersion
```python
class BaselineModelVersion(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True, unique=True)
    description: str = Field(default="")
    pool_type: str = Field(default="residential", index=True)
    active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    climate_profile_id: Optional[int] = Field(default=None, index=True)
    water_profile_id: Optional[int] = Field(default=None, index=True)
```


## `/mnt/data/_extracted/pool_service_pricing_v1/pool_service_pricing_v1/pool_service_pricing_v1/app/services/estimator.py`
Why it matters: pricing_v1 explicit settings and multiplier logic


### EstimateInputs
```python
class EstimateInputs:
    property_id: int
    model_version_id: int
    scenario_name: str
    pool_gallons: float
    visits_per_month: float
    minutes_on_site: float
    drive_minutes_round_trip: float
    techs_on_visit: int
    bath_score: int
    debris_score: int
    filtration_score: int
    overflow_score: int
    annual_backwash_gallons: float
    global_adjustment_pct: float
    target_margin_pct: float
    notes: str = ""
```


### build_chemical_multiplier
```python
def build_chemical_multiplier(
    weights: dict[str, float],
    bath_score: int,
    debris_score: int,
    filtration_score: int,
    overflow_score: int,
    annual_backwash_gallons: float,
    pool_gallons: float,
) -> float:
    bath_pressure = score_to_pressure(bath_score)
    debris_pressure = score_to_pressure(debris_score)
    filtration_pressure = score_to_pressure(filtration_score)
    overflow_pressure = score_to_pressure(overflow_score)
    backwash_pressure = liquid_event_factor(annual_backwash_gallons, pool_gallons)

    weighted_effect = (
        bath_pressure * weights.get("bath", 0.0)
        + debris_pressure * weights.get("debris", 0.0)
        + filtration_pressure * weights.get("filtration", 0.0)
        + overflow_pressure * weights.get("overflow", 0.0)
        + backwash_pressure * weights.get("backwash", 0.0)
    )
    return max(0.30, 1.0 + weighted_effect)
```


### get_system_settings
```python
def get_system_settings(session: Session) -> dict[str, float]:
    rows = session.exec(select(SystemSetting)).all()
    return {row.key: float(row.value) for row in rows}
```


## `/mnt/data/_extracted/pool_volume_tool_live_proto/pool_volume_tool_live_proto/pool_volume_tool_live_proto/pool_volume_tool/service.py`
Why it matters: volume tool evidence and assumption packaging


### PoolVolumeService
```python
class PoolVolumeService:
    permit_connector: PermitConnector
    imagery_connector: ImageryConnector
    live_resolver: LiveDataResolver

    @classmethod
    def build_default(cls) -> "PoolVolumeService":
        return cls(
            permit_connector=MockPermitConnector(),
            imagery_connector=MockImageryConnector(),
            live_resolver=LiveDataResolver(),
        )

    def inspect_live(self, request: EstimateRequest) -> dict:
        return self.live_resolver.inspect(address=request.address, parcel_id=request.parcel_id)

    def estimate(self, request: EstimateRequest) -> EstimateResult:
        permit_records = [*self.permit_connector.fetch(request.address, request.parcel_id), *request.permit_records]
        imagery_measurements = [*self.imagery_connector.fetch(request.address, request.parcel_id), *request.imagery_measurements]

        evidence: list[EvidenceItem] = []
        assumptions: list[str] = []

        if request.use_live_sources and request.address and not permit_records and not imagery_measurements:
            live = self.live_resolver.resolve(address=request.address, parcel_id=request.parcel_id)
            if live.parcel:
                evidence.append(
                    EvidenceItem(
                        source="florida_statewide_parcels_live",
                        evidence_type="parcel",
                        summary="Live parcel geometry and property metadata were found for the requested address.",
                        raw=live.parcel,
                    )
                )
            if live.geocode:
                evidence.append(
```


## `/mnt/data/_extracted/pool_volume_tool_live_proto/pool_volume_tool_live_proto/pool_volume_tool_live_proto/pool_volume_tool/live_sources.py`
Why it matters: volume tool live resolver design


### LiveLookupResult
```python
class LiveLookupResult:
    geocode: dict[str, Any] | None = None
    parcel: dict[str, Any] | None = None
    imagery_measurement: dict[str, Any] | None = None
    permit_records: list[dict[str, Any]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
```


### LiveDataResolver
```python
class LiveDataResolver:
    def __init__(self, timeout_seconds: int = 25) -> None:
        self.timeout_seconds = timeout_seconds
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "pool-volume-tool/0.2 (+local prototype)",
                "Accept": "application/json,image/*,*/*",
            }
        )

    def resolve(self, address: str | None = None, parcel_id: str | None = None) -> LiveLookupResult:
        result = LiveLookupResult()
        try:
            geocode = self._geocode_address(address) if address else None
            result.geocode = geocode
        except Exception as exc:
            result.errors.append(f"Geocoding failed: {exc}")
            geocode = None

        try:
            parcel = self._lookup_parcel(parcel_id=parcel_id, geocode=geocode)
            result.parcel = parcel
        except Exception as exc:
            result.errors.append(f"Parcel lookup failed: {exc}")
            parcel = None

        try:
            county_name = self._county_name(geocode, parcel)
            result.permit_records = self._build_permit_records(address=address, parcel=parcel, county_name=county_name)
        except Exception as exc:
            result.errors.append(f"Permit link generation failed: {exc}")

        try:
            imagery_measurement = self._detect_pool_from_imagery(parcel=parcel, geocode=geocode)
            if imagery_measurement:
```


### detect_pool_surface_area
```python
def detect_pool_surface_area(
    image: Image.Image,
    bbox_mercator: tuple[float, float, float, float],
    parcel_rings_mercator: list[list[tuple[float, float]]] | None = None,
) -> dict[str, Any] | None:
    width, height = image.size
    arr = np.asarray(image).astype(np.int16)

    parcel_mask_img = Image.new("L", (width, height), 0)
    draw = ImageDraw.Draw(parcel_mask_img)
    if parcel_rings_mercator:
        for ring in parcel_rings_mercator:
            if len(ring) < 3:
                continue
            pix_ring = [mercator_to_pixel(x, y, bbox_mercator, image.size) for x, y in ring]
            draw.polygon(pix_ring, fill=255)
    else:
        draw.rectangle([0, 0, width, height], fill=255)
    parcel_mask = np.asarray(parcel_mask_img) > 0

    r = arr[:, :, 0]
    g = arr[:, :, 1]
    b = arr[:, :, 2]
    max_rgb = np.maximum(np.maximum(r, g), b)
    min_rgb = np.minimum(np.minimum(r, g), b)
    chroma = max_rgb - min_rgb

    water_like = (
        (parcel_mask)
        & (b >= 70)
        & (b >= r + 8)
        & (b >= g - 10)
        & (chroma >= 12)
        & (max_rgb <= 245)
        & ((b - r) + (b - g) >= 18)
    )
```


## `/mnt/data/main.py`
Why it matters: bridge backend logic


### init_db
```python
def init_db() -> None:
    conn = get_db()
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA busy_timeout=30000")
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS calls (
            id TEXT PRIMARY KEY,
            rc_event_uuid TEXT,
            telephony_session_id TEXT,
            source_record_id TEXT,
            caller_phone TEXT,
            internal_phone TEXT,
            agent_extension_id TEXT,
            direction TEXT,
            call_time TEXT,
            summary TEXT,
            next_steps TEXT,
            transcript TEXT,
            extracted_address TEXT,
            extracted_names TEXT,
            status TEXT,
            raw_json TEXT,
            attached_contact_ids TEXT,
            created_at TEXT,
            updated_at TEXT
        )
        """
    )
    cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_calls_session ON calls(telephony_session_id)")
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS caller_relationships (
            phone TEXT NOT NULL,
```


### rc_create_subscription
```python
def rc_create_subscription(mode: str = "configured") -> Dict[str, Any]:
    token = rc_access_token()
    event_filters = build_rc_event_filters(mode)
    if not event_filters:
        raise RuntimeError("No RingCentral event filters are enabled. Check your .env toggles or requested mode.")
    body = {
        "eventFilters": event_filters,
        "deliveryMode": {
            "transportType": "WebHook",
            "address": build_rc_webhook_address(),
            "validationToken": RC_VALIDATION_TOKEN,
        },
    }
    resp = requests.post(
        f"{RC_SERVER_URL}/restapi/v1.0/subscription",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        json=body,
        timeout=30,
    )
    try:
        resp.raise_for_status()
    except requests.HTTPError as exc:
        body_text = resp.text.strip()
        raise RuntimeError(
            f"RingCentral subscription failed ({resp.status_code}). mode={mode}. "
            f"filters={json.dumps(event_filters)}. response={body_text}"
        ) from exc
    return resp.json()
```


### lacrm_get_contacts
```python
def lacrm_get_contacts(search_terms: str) -> List[Dict[str, Any]]:
    data = lacrm_call("GetContacts", {"SearchTerms": search_terms})
    if isinstance(data, dict) and "Results" in data:
        return data["Results"] or []
    if isinstance(data, list):
        return data
    return []
```


### lacrm_create_task
```python
def lacrm_create_task(name: str, contact_id: str, due_date: Optional[str] = None, assigned_to: Optional[str] = None, description: str = "") -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "Name": name,
        "ContactId": str(contact_id),
    }
    if due_date:
        payload["DueDate"] = due_date
    if assigned_to:
        payload["AssignedTo"] = str(assigned_to)
    if description:
        payload["Description"] = description
    data = lacrm_call("CreateTask", payload)
    return data if isinstance(data, dict) else {"result": data}
```


### upsert_call
```python
def upsert_call(data: Dict[str, Any]) -> str:
    conn = get_db()
    cur = conn.cursor()
    existing_id = data.get("id")
    if not existing_id and data.get("telephony_session_id"):
        cur.execute("SELECT id FROM calls WHERE telephony_session_id = ?", (data["telephony_session_id"],))
        row = cur.fetchone()
        if row:
            existing_id = row[0]
    if not existing_id and data.get("source_record_id"):
        cur.execute("SELECT id FROM calls WHERE source_record_id = ? ORDER BY COALESCE(updated_at, created_at) DESC LIMIT 1", (data["source_record_id"],))
        row = cur.fetchone()
        if row:
            existing_id = row[0]
    call_id = existing_id or str(uuid.uuid4())
    cur.execute(
        """
        INSERT INTO calls(
            id, rc_event_uuid, telephony_session_id, source_record_id, caller_phone, internal_phone,
            agent_extension_id, direction, call_time, summary, next_steps, transcript,
            extracted_address, extracted_names, status, raw_json, attached_contact_ids,
            created_at, updated_at
        ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        ON CONFLICT(id) DO UPDATE SET
            rc_event_uuid=excluded.rc_event_uuid,
            telephony_session_id=COALESCE(excluded.telephony_session_id, calls.telephony_session_id),
            source_record_id=COALESCE(excluded.source_record_id, calls.source_record_id),
            caller_phone=COALESCE(excluded.caller_phone, calls.caller_phone),
            internal_phone=COALESCE(excluded.internal_phone, calls.internal_phone),
            agent_extension_id=COALESCE(excluded.agent_extension_id, calls.agent_extension_id),
            direction=COALESCE(excluded.direction, calls.direction),
            call_time=COALESCE(excluded.call_time, calls.call_time),
            summary=COALESCE(NULLIF(excluded.summary,''), calls.summary),
            next_steps=COALESCE(NULLIF(excluded.next_steps,''), calls.next_steps),
            transcript=COALESCE(NULLIF(excluded.transcript,''), calls.transcript),
            extracted_address=COALESCE(NULLIF(excluded.extracted_address,''), calls.extracted_address),
```


### get_calls_for_view
```python
def get_calls_for_view(view: str = "active") -> List[Dict[str, Any]]:
    view = (view or "active").lower()
    conn = get_db()
    cur = conn.cursor()
    if view == "processed":
        cur.execute(
            "SELECT * FROM calls WHERE COALESCE(hidden,0)=0 AND status IN ('ATTACHED','AUTO_ATTACHED') ORDER BY COALESCE(updated_at, call_time, created_at) DESC"
        )
    else:
        cur.execute(
            "SELECT * FROM calls WHERE COALESCE(hidden,0)=0 AND status IN ('PENDING_REVIEW','PENDING_INSIGHTS') ORDER BY call_time DESC, created_at DESC"
        )
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows
```


### get_sms_batches
```python
def get_sms_batches(view: str = "active", statuses: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    if statuses is None:
        statuses = ["ATTACHED", "AUTO_ATTACHED"] if (view or "active").lower() == "processed" else ["OPEN", "PENDING_REVIEW"]
    placeholders = ",".join(["?" for _ in statuses])
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        f"SELECT * FROM sms_batches WHERE COALESCE(hidden,0)=0 AND status IN ({placeholders}) ORDER BY COALESCE(updated_at, latest_message_at, created_at) DESC",
        tuple(statuses),
    )
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    for row in rows:
        row["routing_rule"] = get_routing_rule(row.get("external_phone") or "")
    return rows
```


### rc_message_sync
```python
def rc_message_sync(sync_type: str, sync_token: Optional[str] = None, date_from: Optional[str] = None) -> Dict[str, Any]:
    """RingCentral Message Sync API.
    We use it to pull BOTH inbound and outbound SMS so the UI shows the full conversation thread.
    """
    token = rc_access_token()
    url = f"{RC_SERVER_URL}/restapi/v1.0/account/~/extension/~/message-sync"
    params: Dict[str, Any] = {"syncType": sync_type, "messageType": "SMS"}
    if sync_type == "FSync":
        if date_from:
            params["dateFrom"] = date_from
    else:
        if not sync_token:
            raise RuntimeError("ISync requires sync_token")
        params["syncToken"] = sync_token
    resp = requests.get(url, headers={"Authorization": f"Bearer {token}", "Accept": "application/json"}, params=params, timeout=30)
    resp.raise_for_status()
    return resp.json()
```


## `/mnt/data/app.js`
Why it matters: bridge front desk queue and client-side workflow state.


### pattern: const state =
```javascript
}
function renderIdentity(prefix, phone, candidates, attachedIds = [], routingRule = null) {
  const state = buildIdentityState(phone, candidates, attachedIds, routingRule);
  const box = document.getElementById(`${prefix}IdentityBox`);
  const phoneEl = document.getElementById(`${prefix}IdentityPhone`);
  const nameEl = document.getElementById(`${prefix}IdentityName`);
  const badgeEl = document.getElementById(`${prefix}IdentityBadge`);
  const subEl = document.getElementById(`${prefix}IdentitySub`);
  const noteEl = document.getElementById(`${prefix}IdentityNote`);
  const badge = certaintyPresentation(state.level);
  phoneEl.textContent = state.phone || "";
  nameEl.textContent = state.name || "";
  subEl.textContent = state.subtitle || "";
  noteEl.textContent = state.note || "";
  badgeEl.textContent = badge.label;
  badgeEl.className = `certainty-badge ${badge.cls}`;
  box.classList.remove("hidden");
}
function renderHudIdentity(item) {
  const state = buildIdentityState(item?.caller_phone || '', item?.candidates || [], [], item?.routing_rule || null);
  const badge = certaintyPresentation(state.level);
  document.getElementById('hudIdentityPhone').textContent = state.phone || '';
  document.getElementById('hudIdentityName').textContent = state.name || '';
  document.getElementById('hudIdentitySub').textContent = state.subtitle || '';
  document.getElementById('hudIdentityNote').textContent = state.note || '';
  const badgeEl = document.getElementById('hudIdentityBadge');
  badgeEl.textContent = badge.label;
  badgeEl.className = `certainty-badge ${badge.cls}`;
}
function hideIncomingHud() {
```


## `/mnt/data/index.html`
Why it matters: active bridge UI shell.

```html
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Keys Pool Service Data Hub</title>
  <link rel="stylesheet" href="/static/styles.css">
</head>
<body>
  <header>
    <div class="brand-wrap">
      <img src="/static/keyspool-logo.png" alt="Keys Pool Service logo" class="brand-logo">
      <div class="brand-copy">
        <h1>Keys Pool Service Data Hub</h1>
        <p class="brand-subtitle">Powered by Kristoffer™</p>
      </div>
    </div>
    <div class="header-actions">
      <div class="inline-help-wrap">
        <button id="runEodBtn" class="secondary">Run end-of-day text batch now</button>
        <button type="button" class="help-chip" title="Creates or refreshes end-of-day text summaries for open text threads. Use this when you want today's messages grouped and summarized now." data-help="Creates or refreshes end-of-day text summaries for open text threads. Use this when you want today's messages grouped and summarized now.">?</button>
      </div>
      <div class="inline-help-wrap">
        <button id="refreshBtn">Refresh</button>
        <button type="button" class="help-chip" title="Refreshes the queue right now so you can see any new calls or text summaries without waiting for auto-refresh." data-help="Refreshes the queue right now so you can see any new calls or text summaries without waiting for auto-refresh.">?</button>
      </div>
    </div>
  </header>



  <div id="incomingHud" class="hud-overlay hidden">
    <div class="hud-card">
      <div class="hud-top">
        <div>
          <div class="hud-eyebrow">Incoming call context</div>
          <h2 id="hudCallerTitle">Unknown caller</h2>
          <div id="hudMeta" class="meta"></div>
        </div>
        <div class="hud-actions">
          <span id="hudStatusBadge" class="certainty-badge suggested">Ringing</span>
          <button id="hudDismissBtn" class="secondary">Dismiss</button>
        </div>
      </div>
      <div class="hud-grid">
        <div class="hud-section">
          <h3>Likely CRM match</h3>
          <div id="hudIdentityBox" class="identity-box">
            <div class="identity-line">
              <span id="hudIdentityPhone" class="identity-phone"></span>
              <span class="identity-sep">—</span>
              <strong id="hudIdentityName" class="identity-name"></strong>
              <span id="hudIdentityBadge" class="certainty-badge unknown">No match</span>
            </div>
            <div id="hudIdentitySub" class="small"></div>
            <div id="hudIdentityNote" class="small"></div>
          </div>
          <div id="hudOpenTaskHint" class="urgency-badge hidden">Open follow-up items on this profile</div>
        </div>
        <div class="hud-section">
          <h3>Last 5 CRM entries</h3>
          <div id="hudHistoryList" class="hud-history-list"></div>
        </div>
      </div>
    </div>
  </div>

  <main class="layout">
    <section class="panel queue-panel">
      <div class="tab-row">
        <button id="tabCalls" class="tab active">Calls + voicemail</button>
        <button id="tabTexts" class="tab secondary">Text summaries</button>
      </div>
      <div class="view-row">
        <button id="viewActiveBtn" class="subtab active">Active calls</button>
        <button id="viewProcessedBtn" class="subtab secondary">Processed history</button>
      </div>
      <div id="queueTitle" class="queue-title">Pending calls</div>
      <div id="queue" class="queue"></div>
    </section>

    <section class="panel detail-panel">
      <div id="emptyState" class="empty">Select an item from the left.</div>

      <div id="callDetail" class="hidden">
        <div class="detail-top">
          <div>
            <h2 id="callTitle">Call</h2>
            <div class="meta" id="callMeta"></div>
            <div id="callIdentityBox" class="identity-box hidden">
              <div class="identity-line">
                <span id="callIdentityPhone" class="identity-phone"></span>
                <span class="identity-sep">—</span>
                <strong id="callIdentityName" class="identity-name"></strong>
                <span id="callIdentityBadge" class="certainty-badge unknown">No match</span>
              </div>
              <div id="callIdentitySub" class="small"></div>
              <div id="callIdentityNote" class="small"></div>
            </div>
          </div>
          <div class="detail-actions detail-actions-stack">
            <span id="callStatusBadge" class="badge"></span>
            <div class="inline-help-wrap"><button id="callCreateTaskBtn" class="secondary">Create task</button><button type="button" class="help-chip" title="Creates a follow-up task in Less Annoying CRM for the current or selected contact using this conversation as context." data-help="Creates a follow-up task in Less Annoying CRM for the current or selected contact using this conversation as context.">?</button></div>
            <div class="inline-help-wrap"><button id="callTrashBtn" class="secondary danger-btn">Trash / dismiss</button><button type="button" class="help-chip" title="Hides this call from the queue without saving it to CRM. Use this for spam, robocalls, or promotional calls that should not be kept in the working queue." data-help="Hides this call from the queue without saving it to CRM. Use this for spam, robocalls, or promotional calls that should not be kept in the working queue.">?</button></div>
          </div>
        </div>
        <div class="cards">
          <div class="card">
          <h3 id="callSummaryHeading">Summary</h3>
          <div id="callSummaryText"></div>
        </div>
        <div class="card">
          <h3 id="callNextStepsHeading">Next steps</h3>
          <div id="callNextStepsText"></div>
        </div>
        </div>
        <div class="cards">
          <div class="card">
          <h3 id="callTranscriptHeading">Transcript</h3>
          <div id="callTranscriptText"></div>
```


## `/mnt/data/styles.css`
Why it matters: active bridge visual structure.

```css

:root {
  --bg: #0f172a;
  --panel: #111827;
  --panel-2: #1f2937;
  --text: #e5e7eb;
  --muted: #94a3b8;
  --border: #334155;
  --accent: #22c55e;
  --accent-2: #38bdf8;
  --warn: #f59e0b;
  --danger: #ef4444;
}
* { box-sizing: border-box; }
body { margin: 0; font-family: Inter, system-ui, Arial, sans-serif; background: var(--bg); color: var(--text); }
header { display: flex; justify-content: space-between; gap: 16px; align-items: center; padding: 18px 22px; border-bottom: 1px solid var(--border); background: #0b1220; position: sticky; top: 0; z-index: 10; }
header h1 { margin: 0 0 4px 0; font-size: 22px; }
header p { margin: 0; color: var(--muted); }

.brand-wrap { display: flex; align-items: center; gap: 14px; }
.brand-logo { width: 56px; height: 56px; object-fit: contain; flex: 0 0 56px; }
.brand-copy { display: grid; gap: 2px; }
.brand-subtitle { margin: 0; color: var(--muted); font-size: 13px; }
.header-actions, .inline-help-wrap { display: flex; gap: 8px; align-items: center; }
button { background: var(--accent-2); color: #021018; border: 0; padding: 10px 14px; border-radius: 10px; cursor: pointer; font-weight: 700; }
button.secondary, .tab.secondary { background: transparent; color: var(--text); border: 1px solid var(--border); }
button.attach { background: var(--accent); color: #05210f; }
button.auto { background: #fcd34d; color: #231706; }
button.favorite { background: #a78bfa; color: #130925; }
button:hover { filter: brightness(1.05); }
.help-chip { width: 28px; height: 28px; border-radius: 999px; padding: 0; background: transparent; color: var(--text); border: 1px solid var(--border); font-weight: 800; cursor: help; }
.help-chip:hover { background: rgba(255,255,255,.06); }
.layout { display: grid; grid-template-columns: 340px 1fr; gap: 16px; padding: 16px; }
.panel { background: var(--panel); border: 1px solid var(--border); border-radius: 16px; padding: 16px; min-height: calc(100vh - 120px); }
.tab-row { display: flex; gap: 8px; margin-bottom: 12px; }
.tab.active { background: var(--accent-2); color: #021018; border: 0; }
.queue-title { color: var(--muted); font-size: 14px; margin-bottom: 10px; }
.queue { display: grid; gap: 10px; }
.queue-item { padding: 12px; border: 1px solid var(--border); border-radius: 12px; background: var(--panel-2); cursor: pointer; }
.queue-item.active { outline: 2px solid var(--accent-2); }
.queue-head { display: flex; justify-content: space-between; align-items: start; gap: 10px; margin-bottom: 4px; }
.queue-item h4 { margin: 0; }
.queue-item .small { color: var(--muted); font-size: 13px; }
.empty { display: grid; place-items: center; min-height: 240px; color: var(--muted); border: 1px dashed var(--border); border-radius: 12px; }
.hidden { display: none !important; }
.detail-top { display: flex; justify-content: space-between; gap: 16px; align-items: start; }
.detail-actions { display: flex; gap: 8px; align-items: center; }
.meta, .small { color: var(--muted); font-size: 14px; margin-top: 6px; }
.block-space { margin-bottom: 12px; }
.hint { line-height: 1.45; }
.badge { display: inline-block; padding: 6px 10px; border-radius: 999px; background: rgba(245,158,11,0.15); color: #fcd34d; border: 1px solid rgba(245,158,11,0.4); }
.identity-box { margin-top: 10px; padding: 10px 12px; border-radius: 12px; border: 1px solid var(--border); background: rgba(56,189,248,0.06); }
.identity-line { display: flex; flex-wrap: wrap; align-items: center; gap: 8px; }
.identity-phone { color: #bfdbfe; font-weight: 700; }
.identity-name { font-size: 16px; }
.identity-sep { color: var(--muted); }
.cards { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-top: 16px; }
.card { background: var(--panel-2); border: 1px solid var(--border); border-radius: 14px; padding: 14px; margin-top: 16px; }
.card h3 { margin-top: 0; }
.card-header { display: flex; justify-content: space-between; align-items: center; gap: 12px; }
pre { white-space: pre-wrap; word-break: break-word; margin: 0; color: #d1fae5; font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 13px; line-height: 1.45; }
ul { margin: 0; padding-left: 18px; }
.search-row { display: flex; gap: 10px; }
input[type="text"] { flex: 1; background: #0b1220; border: 1px solid var(--border); color: var(--text); border-radius: 10px; padding: 11px 12px; }
.match-row { display: flex; justify-content: space-between; gap: 10px; padding: 12px 0; border-bottom: 1px solid var(--border); align-items: flex-start; }
.match-row:last-child { border-bottom: 0; }
.match-info h4 { margin: 0 0 4px 0; }
.score { color: #86efac; font-weight: 800; margin-top: 6px; }
.reason-list { color: var(--muted); font-size: 12px; margin-top: 6px; }
.match-actions { display: flex; flex-direction: column; gap: 10px; min-width: 190px; }
.action-stack { display: flex; align-items: center; gap: 6px; }
.action-stack button:first-child { flex: 1; }
.rule-buttons { display: flex; gap: 8px; flex-wrap: wrap; }
.certainty-badge { display: inline-flex; align-items: center; justify-content: center; padding: 5px 10px; border-radius: 999px; border: 1px solid transparent; font-size: 12px; font-weight: 800; }
.certainty-badge.compact { white-space: nowrap; font-size: 11px; padding: 4px 8px; }
.certainty-badge.confirmed { background: rgba(34,197,94,.15); color: #86efac; border-color: rgba(34,197,94,.35); }
.certainty-badge.suggested { background: rgba(56,189,248,.15); color: #bae6fd; border-color: rgba(56,189,248,.35); }
.certainty-badge.multiple { background: rgba(245,158,11,.15); color: #fcd34d; border-color: rgba(245,158,11,.35); }
.certainty-badge.unknown { background: rgba(148,163,184,.15); color: #cbd5e1; border-color: rgba(148,163,184,.35); }
.certainty-badge.manual { background: rgba(244,114,182,.14); color: #f9a8d4; border-color: rgba(244,114,182,.35); }
.certainty-badge.auto { background: rgba(167,139,250,.16); color: #ddd6fe; border-color: rgba(167,139,250,.35); }
.toast { position: fixed; right: 20px; bottom: 20px; background: #052e16; color: #dcfce7; padding: 12px 14px; border-radius: 12px; border: 1px solid rgba(34,197,94,.35); opacity: 0; transform: translateY(12px); transition: .2s ease; pointer-events: none; z-index: 50; max-width: 420px; }
.toast.error { background: #3f0f12; color: #fecaca; border-color: rgba(239,68,68,.35); }
.toast.show { opacity: 1; transform: translateY(0); }
.modal-overlay { position: fixed; inset: 0; background: rgba(2,6,23,.7); display: grid; place-items: center; padding: 18px; z-index: 60; }
.modal-card { width: min(560px, 100%); background: #0b1220; border: 1px solid var(--border); border-radius: 16px; padding: 18px; box-shadow: 0 30px 80px rgba(0,0,0,.35); }
.small-modal { width: min(480px, 100%); }
.modal-header { display: flex; justify-content: space-between; align-items: center; gap: 12px; }
.modal-header h3 { margin: 0; }
.modal-copy { color: var(--text); line-height: 1.55; margin: 14px 0 0 0; }
.modal-actions { display: flex; justify-content: flex-end; gap: 10px; margin-top: 18px; }
.confirm-btn.warn { background: #f59e0b; color: #271504; }
.confirm-btn.confirm { background: #22c55e; color: #05210f; }
@media (max-width: 1100px) {
  .layout { grid-template-columns: 1fr; }
  .panel { min-height: auto; }
  .cards { grid-template-columns: 1fr; }
  .match-row { flex-direction: column; }
  .match-actions { width: 100%; }
}

button.danger-btn, .danger-btn { background: rgba(239,68,68,.12); color: #fecaca; border: 1px solid rgba(239,68,68,.35); }
.detail-actions-stack { flex-direction: column; align-items: stretch; min-width: 190px; }
.queue-item { position: relative; }
.queue-trash { position: absolute; top: 10px; right: 10px; width: 30px; height: 30px; border-radius: 999px; padding: 0; background: transparent; color: var(--muted); border: 1px solid var(--border); }
.queue-trash:hover { color: #fecaca; border-color: rgba(239,68,68,.35); background: rgba(239,68,68,.08); }
.queue-head.with-trash { padding-right: 42px; }
.task-form { display: grid; gap: 14px; margin-top: 14px; }
.task-context-box { border: 1px solid var(--border); background: rgba(56,189,248,.06); border-radius: 12px; padding: 12px; color: var(--text); display: grid; gap: 6px; }
.preset-row { display: flex; flex-wrap: wrap; gap: 8px; }
.form-label { display: grid; gap: 6px; color: var(--text); font-weight: 600; }
.task-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
select, textarea, input[type="date"] { background: #0b1220; border: 1px solid var(--border); color: var(--text); border-radius: 10px; padding: 11px 12px; width: 100%; }
textarea { resize: vertical; min-height: 120px; }
.check-row { color: var(--muted); font-size: 14px; }
.urgency-badge { display: inline-flex; align-items: center; padding: 5px 10px; border-radius: 999px; background: rgba(239,68,68,.14); color: #fecaca; border: 1px solid rgba(239,68,68,.3); font-size: 12px; font-weight: 800; }
.toast.info { background: #082f49; color: #dbeafe; border-color: rgba(56,189,248,.35); }
@media (max-width: 1100px) {
  .task-grid { grid-template-columns: 1fr; }
  .detail-actions-stack { min-width: 0; }
}


.view-row {
  display: flex;
  gap: 8px;
  margin: 10px 0 12px;
}

.subtab {
  border: 1px solid #d7ddea;
  background: #f6f8fc;
  color: #22304d;
  border-radius: 999px;
  padding: 8px 12px;
  font-size: 0.9rem;
  font-weight: 600;
  cursor: pointer;
}

.subtab.active {
  background: #153a7a;
  color: #fff;
  border-color: #153a7a;
}

.subtab.secondary {
  background: #eef3fb;
  color: #22304d;
}


.hud-overlay { position: fixed; inset: 0; background: rgba(2, 6, 23, 0.48); display: grid; place-items: start center; padding: 24px; z-index: 55; pointer-events: none; }
.hud-card { width: min(980px, 100%); background: rgba(8, 15, 30, 0.98); border: 1px solid rgba(56, 189, 248, 0.22); border-radius: 18px; box-shadow: 0 24px 80px rgba(0,0,0,0.35); padding: 18px; pointer-events: auto; }
.hud-top { display: flex; justify-content: space-between; gap: 16px; align-items: start; margin-bottom: 14px; }
.hud-eyebrow { font-size: 12px; text-transform: uppercase; letter-spacing: .08em; color: #7dd3fc; margin-bottom: 6px; }
.hud-actions { display: flex; align-items: center; gap: 10px; }
.hud-grid { display: grid; grid-template-columns: 340px 1fr; gap: 16px; }
.hud-section { background: rgba(15, 23, 42, 0.72); border: 1px solid rgba(148, 163, 184, .18); border-radius: 14px; padding: 14px; }
.hud-section h3 { margin: 0 0 10px 0; font-size: 16px; }
```
