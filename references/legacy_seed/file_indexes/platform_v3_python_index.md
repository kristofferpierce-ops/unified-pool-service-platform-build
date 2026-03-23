# platform_v3 python index

## `app/__init__.py`
- lines: 0
- classes: none
- top-level functions: none

## `app/api/__init__.py`
- lines: 0
- classes: none
- top-level functions: none

## `app/api/main.py`
- lines: 15
- classes: none
- top-level functions: none

## `app/api/routes/__init__.py`
- lines: 0
- classes: none
- top-level functions: none

## `app/api/routes/baseline.py`
- lines: 15
- classes: none
- top-level functions: get_baseline_models

## `app/api/routes/commercial.py`
- lines: 21
- classes: none
- top-level functions: get_orders, get_deliveries

## `app/api/routes/expenses.py`
- lines: 16
- classes: none
- top-level functions: get_expenses

## `app/api/routes/invoices.py`
- lines: 21
- classes: none
- top-level functions: get_invoice_documents, get_invoice_staging

## `app/api/routes/properties.py`
- lines: 27
- classes: none
- top-level functions: get_accounts, get_properties, get_vessels

## `app/api/routes/reports.py`
- lines: 20
- classes: none
- top-level functions: direct_deliveries

## `app/api/routes/tools.py`
- lines: 45
- classes: none
- top-level functions: get_tools, get_property_verifications, post_property_verification

## `app/core/__init__.py`
- lines: 0
- classes: none
- top-level functions: none

## `app/core/config.py`
- lines: 13
- classes: none
- top-level functions: none

## `app/core/database.py`
- lines: 18
- classes: none
- top-level functions: create_db_and_tables, get_session

## `app/models/__init__.py`
- lines: 0
- classes: none
- top-level functions: none

## `app/models/tables.py`
- lines: 368
- classes: ExpenseItem, ChemicalProduct, ProductPriceHistory, ClimateProfile, WaterProfile, BaselineModelVersion, Account, Property, PoolVessel, EquipmentAsset, EstimateScenario, EstimateRun, WaterTestLog, ChemicalUsageLog, ServiceLog, CalibrationAdjustment, CommercialVendorOrder, CommercialVendorOrderItem, CommercialDelivery, CommercialDeliveryItem, InventorySnapshot, InvoiceDocument, InvoiceLineStaging, SupplierTrainingExample, ToolCatalogEntry, ToolRun, ApprovedAgent, PropertyVerificationCase
- top-level functions: none

## `app/services/__init__.py`
- lines: 0
- classes: none
- top-level functions: none

## `app/services/baseline.py`
- lines: 75
- classes: none
- top-level functions: score_to_pressure, get_active_model, load_model_payload, build_condition_multiplier, estimate_chemical_quantities

## `app/services/bootstrap.py`
- lines: 123
- classes: none
- top-level functions: seed_defaults

## `app/services/calibration.py`
- lines: 86
- classes: none
- top-level functions: compare_estimate_to_actual, save_suggested_calibration, account_calibration_map

## `app/services/commercial.py`
- lines: 115
- classes: none
- top-level functions: create_vendor_order, add_vendor_order_item, create_delivery, add_delivery_item, direct_delivery_report_dataframe, export_direct_delivery_report_xlsx

## `app/services/estimator.py`
- lines: 179
- classes: LaborSettings, EstimateInput, EstimateOutput
- top-level functions: burdened_labor_rate, service_time_multiplier, calculate_estimate, save_estimate_run

## `app/services/expenses.py`
- lines: 48
- classes: none
- top-level functions: list_expenses, annual_overhead_total, overhead_per_billable_hour, latest_unit_cost, create_price_history

## `app/services/invoice_ingestion.py`
- lines: 199
- classes: none
- top-level functions: _extract_text, ingest_invoice_document, _product_candidates, _property_candidates, stage_invoice_lines, bucket_counts, approve_staged_line, reject_staged_line

## `app/services/property_verification.py`
- lines: 239
- classes: VerificationDecision
- top-level functions: normalize_name, looks_like_entity, person_name_match, build_property_search_url, build_gis_url, build_sunbiz_entity_search_url, build_source_links, list_approved_agents, add_approved_agent, evaluate_verification, create_verification_case, list_verification_cases

## `app/services/tools.py`
- lines: 79
- classes: ToolDefinition
- top-level functions: seed_tools, list_tools, log_tool_run

## `app/utils/__init__.py`
- lines: 0
- classes: none
- top-level functions: none

## `app/utils/matching.py`
- lines: 29
- classes: none
- top-level functions: normalize_text, similarity, best_match

## `app/utils/serialization.py`
- lines: 17
- classes: none
- top-level functions: dumps, loads

## `scripts/init_db.py`
- lines: 15
- classes: none
- top-level functions: main

## `tests/test_property_verification.py`
- lines: 27
- classes: none
- top-level functions: test_person_name_match_exact, test_verified_owner_status, test_entity_likely_authorized_agent

## `tests/test_services.py`
- lines: 13
- classes: none
- top-level functions: test_score_to_pressure, test_condition_multiplier_positive

## `ui/app.py`
- lines: 37
- classes: none
- top-level functions: none

## `ui/pages/1_Admin_Costs.py`
- lines: 79
- classes: none
- top-level functions: none

## `ui/pages/2_Baseline_Models.py`
- lines: 35
- classes: none
- top-level functions: none

## `ui/pages/3_Accounts_&_Properties.py`
- lines: 80
- classes: none
- top-level functions: none

## `ui/pages/4_Residential_Estimator.py`
- lines: 86
- classes: none
- top-level functions: none

## `ui/pages/5_Commercial_Estimator.py`
- lines: 105
- classes: none
- top-level functions: none

## `ui/pages/6_Commercial_Deliveries.py`
- lines: 85
- classes: none
- top-level functions: none

## `ui/pages/7_Invoice_Review.py`
- lines: 51
- classes: none
- top-level functions: none

## `ui/pages/8_Compare_&_Train.py`
- lines: 71
- classes: none
- top-level functions: none

## `ui/pages/9_Tools.py`
- lines: 156
- classes: none
- top-level functions: none
