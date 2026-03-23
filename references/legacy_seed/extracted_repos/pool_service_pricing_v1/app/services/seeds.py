DEFAULT_SYSTEM_SETTINGS = {
    "tech_hourly_wage": {"value": 22.0, "description": "Base route technician hourly wage"},
    "payroll_tax_burden_pct": {"value": 10.0, "description": "Payroll tax burden percentage"},
    "benefits_burden_pct": {"value": 5.0, "description": "Benefits burden percentage"},
    "billable_hours_per_tech_per_year": {"value": 1500.0, "description": "Annual billable hours per route technician"},
    "number_of_route_techs": {"value": 4.0, "description": "Number of technicians used for overhead allocation"},
    "target_margin_pct": {"value": 35.0, "description": "Default target gross margin"},
}

DEFAULT_COMPANY_EXPENSES = {
    "insurance": {
        "auto_policy": 25000.0,
        "general_liability": 20000.0,
        "workers_comp": 20000.0,
    },
    "vehicle": {
        "fuel": 18000.0,
        "maintenance_repairs": 9000.0,
        "registration_tolls": 2500.0,
    },
    "operations": {
        "testing_supplies": 4000.0,
        "tools_equipment": 5000.0,
        "uniforms_shirts": 1200.0,
        "phones_tablets": 2400.0,
        "software_subscriptions": 1800.0,
        "office_internet": 1800.0,
        "office_rent": 0.0,
        "utilities": 1200.0,
    },
    "admin": {
        "management_admin_labor": 25000.0,
        "bookkeeping_payroll": 3500.0,
        "marketing": 1500.0,
        "licenses_permits": 800.0,
    },
}

DEFAULT_CHEMICALS = {
    "liquid_chlorine_12pct_gal": {"display_name": "Liquid Chlorine 12%", "unit_name": "gal", "unit_cost": 4.25},
    "muriatic_acid_gal": {"display_name": "Muriatic Acid", "unit_name": "gal", "unit_cost": 8.00},
    "sodium_bicarbonate_lb": {"display_name": "Sodium Bicarbonate", "unit_name": "lb", "unit_cost": 0.75},
    "cyanuric_acid_lb": {"display_name": "Cyanuric Acid", "unit_name": "lb", "unit_cost": 3.25},
    "calcium_chloride_lb": {"display_name": "Calcium Chloride", "unit_name": "lb", "unit_cost": 1.15},
    "algaecide_oz": {"display_name": "Algaecide", "unit_name": "oz", "unit_cost": 0.22},
    "phosphate_remover_oz": {"display_name": "Phosphate Remover", "unit_name": "oz", "unit_cost": 0.50},
}

DEFAULT_WATER_PROFILE = {
    "name": "FKAA Key West Starting Profile",
    "source_name": "Florida Keys Aqueduct Authority",
    "ph": 9.0,
    "total_alkalinity_ppm": 50.0,
    "calcium_hardness_ppm": 86.0,
    "tds_ppm": 230.0,
    "chloride_ppm": 50.0,
    "sodium_ppm": 22.0,
    "notes": "Starting profile based on public FKAA finished-water figures used as a practical estimator baseline.",
}

DEFAULT_CLIMATE_PROFILE = {
    "name": "Key West Historical Climate v1",
    "location_name": "Key West, Florida",
    "avg_annual_rain_inches": 40.44,
    "avg_uv_index": 8.8,
    "avg_air_temp_f": 78.1,
    "notes": "Historical Key West climate baseline for outdoor pool estimating.",
}

DEFAULT_BASELINE_MODEL = {
    "name": "Residential Key West Baseline v1",
    "description": "Residential baseline model using Key West climate and FKAA makeup-water assumptions.",
    "pool_type": "residential",
}

DEFAULT_CHEMICAL_COEFFICIENTS = {
    "liquid_chlorine_12pct_gal": 0.00809,
    "muriatic_acid_gal": 0.00162,
    "sodium_bicarbonate_lb": 0.00192,
    "cyanuric_acid_lb": 0.0000615,
    "calcium_chloride_lb": 0.000576,
    "algaecide_oz": 0.002598,
    "phosphate_remover_oz": 0.000800,
}

DEFAULT_CHEMICAL_WEIGHTS = {
    "liquid_chlorine_12pct_gal": {"bath": 0.40, "debris": 0.25, "filtration": 0.35, "overflow": 0.08, "backwash": 0.02},
    "muriatic_acid_gal": {"bath": 0.20, "debris": 0.15, "filtration": 0.25, "overflow": 0.05, "backwash": 0.00},
    "sodium_bicarbonate_lb": {"bath": 0.12, "debris": 0.10, "filtration": 0.22, "overflow": 0.20, "backwash": 0.10},
    "cyanuric_acid_lb": {"bath": 0.05, "debris": 0.10, "filtration": 0.05, "overflow": 0.40, "backwash": 0.30},
    "calcium_chloride_lb": {"bath": 0.05, "debris": 0.05, "filtration": 0.08, "overflow": 0.35, "backwash": 0.20},
    "algaecide_oz": {"bath": 0.15, "debris": 0.45, "filtration": 0.35, "overflow": 0.00, "backwash": 0.00},
    "phosphate_remover_oz": {"bath": 0.20, "debris": 0.55, "filtration": 0.25, "overflow": 0.00, "backwash": 0.00},
}
