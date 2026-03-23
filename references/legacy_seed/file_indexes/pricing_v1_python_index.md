# pricing_v1 python index

## `app/__init__.py`
- lines: 0
- classes: none
- top-level functions: none

## `app/api/__init__.py`
- lines: 0
- classes: none
- top-level functions: none

## `app/api/main.py`
- lines: 16
- classes: none
- top-level functions: health

## `app/api/routes/__init__.py`
- lines: 0
- classes: none
- top-level functions: none

## `app/api/routes/admin.py`
- lines: 19
- classes: none
- top-level functions: list_settings, list_expenses

## `app/api/routes/estimates.py`
- lines: 12
- classes: none
- top-level functions: estimate

## `app/api/routes/properties.py`
- lines: 32
- classes: none
- top-level functions: list_properties, create_property, get_property

## `app/core/__init__.py`
- lines: 0
- classes: none
- top-level functions: none

## `app/core/config.py`
- lines: 7
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
- lines: 125
- classes: SystemSetting, CompanyExpense, ChemicalCatalog, WaterProfile, ClimateProfile, BaselineModelVersion, ChemicalCoefficient, ChemicalWeight, Property, EstimateRun, FieldObservation
- top-level functions: none

## `app/services/__init__.py`
- lines: 0
- classes: none
- top-level functions: none

## `app/services/bootstrap.py`
- lines: 92
- classes: none
- top-level functions: seed_defaults

## `app/services/calibration.py`
- lines: 53
- classes: none
- top-level functions: compare_estimate_to_observations

## `app/services/estimator.py`
- lines: 212
- classes: EstimateInputs
- top-level functions: score_to_pressure, liquid_event_factor, build_chemical_multiplier, get_system_settings, get_company_expenses_total, get_chemical_unit_costs, calculate_burdened_labor_rate, calculate_overhead_per_hour, service_time_multiplier, run_estimate, save_estimate_run

## `app/services/repositories.py`
- lines: 96
- classes: none
- top-level functions: get_all, get_system_settings, upsert_system_setting, get_active_baseline_model, get_model_coefficients, get_model_weights, get_chemical_catalog, get_property, get_estimate_runs_for_property, get_observations_for_property

## `app/services/seeds.py`
- lines: 94
- classes: none
- top-level functions: none

## `scripts/seed_database.py`
- lines: 20
- classes: none
- top-level functions: main

## `ui/app.py`
- lines: 554
- classes: none
- top-level functions: load_properties, load_company_expenses, load_settings, load_chemical_catalog, load_model_versions, load_model_coefficients, load_model_weights, clear_caches
