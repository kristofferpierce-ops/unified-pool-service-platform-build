from __future__ import annotations

from sqlmodel import Session, select

from app.models.connector_tables import SourceSystem
from app.models.tables import BaselineModelVersion, ChemicalProduct, ClimateProfile, ExpenseItem, WaterProfile
from app.services.quote_workflow import ensure_quote_workflow_settings
from app.services.system_settings import set_setting
from app.services.tools import seed_tools
from app.utils.serialization import dumps

DEFAULT_EXPENSES = [
    ('insurance', 'auto_policy', 25000.0),
    ('insurance', 'general_liability', 20000.0),
    ('insurance', 'workers_comp', 20000.0),
    ('vehicle', 'fuel', 18000.0),
    ('vehicle', 'maintenance_repairs', 9000.0),
    ('operations', 'testing_supplies', 4000.0),
    ('operations', 'uniforms_shirts', 1200.0),
    ('operations', 'software_subscriptions', 1800.0),
    ('operations', 'office_internet', 1800.0),
    ('operations', 'office_rent', 0.0),
    ('admin', 'management_admin_labor', 25000.0),
    ('admin', 'bookkeeping_payroll', 3500.0),
]

DEFAULT_PRODUCTS = [
    ('LIQ-CL-12', 'Liquid Chlorine 12%', 'gal', 4.25, 'Generic', '12PCT-LIQ-CL', 'chemical', 'chlorine, sodium hypochlorite 12%'),
    ('MURI-ACID', 'Muriatic Acid', 'gal', 8.0, 'Generic', 'HCL-31', 'chemical', 'hydrochloric acid, muriatic'),
    ('SOD-BICARB', 'Sodium Bicarbonate', 'lb', 0.75, 'Generic', 'NAHCO3', 'chemical', 'bicarb, baking soda'),
    ('CYA-GRAN', 'Cyanuric Acid', 'lb', 3.25, 'Generic', 'CYA-100', 'chemical', 'stabilizer, conditioner'),
    ('CAL-CHL', 'Calcium Chloride', 'lb', 1.15, 'Generic', 'CACL2', 'chemical', 'hardness increaser'),
    ('ALGAE-POLY', 'Polyquat Algaecide', 'oz', 0.22, 'Generic', 'POLYQUAT60', 'chemical', 'algaecide'),
    ('PHOS-REM', 'Phosphate Remover', 'oz', 0.50, 'Generic', 'PHOSREM', 'chemical', 'phosphate remover'),
    ('CHEM-CLEAN-EXP', 'Chem Clean Express', 'oz', 0.35, 'Generic', 'CHEMCLEANEXP', 'chemical', 'clean up, cleanup, express'),
]

DEFAULT_SOURCE_SYSTEMS = [
    ('ringcentral', 'RingCentral', 'communications'),
    ('lacrm', 'Less Annoying CRM', 'crm'),
    ('freshbooks', 'FreshBooks', 'billing'),
    ('skimmer', 'Skimmer', 'operations'),
    ('heritage', 'Heritage Pool Plus', 'vendor'),
    ('invoice_import', 'Invoice Import', 'document'),
    ('quickbooks', 'QuickBooks Desktop', 'accounting'),
]

DEFAULT_LABOR_SETTINGS = {
    'tech_hourly_wage': 22.0,
    'payroll_tax_burden_pct': 10.0,
    'benefits_burden_pct': 5.0,
    'billable_hours_per_tech_per_year': 1500.0,
    'number_of_route_techs': 4,
}


def seed_defaults(session: Session) -> None:
    if not session.exec(select(ExpenseItem)).first():
        for category, name, annual_cost in DEFAULT_EXPENSES:
            session.add(ExpenseItem(category=category, name=name, annual_cost=annual_cost))

    if not session.exec(select(ChemicalProduct)).first():
        for sku, name, unit, unit_cost, manufacturer, mpn, family, aliases in DEFAULT_PRODUCTS:
            session.add(ChemicalProduct(
                sku=sku,
                name=name,
                unit=unit,
                default_unit_cost=unit_cost,
                manufacturer=manufacturer,
                manufacturer_part_number=mpn,
                product_family=family,
                aliases_csv=aliases,
            ))

    climate = session.exec(select(ClimateProfile).where(ClimateProfile.name == 'Key West Baseline')).first()
    if not climate:
        climate = ClimateProfile(
            name='Key West Baseline',
            location='Key West, FL',
            monthly_temperature_csv='70.6,72.3,75.7,78.8,81.6,83.9,85.1,85.5,84.1,81.2,76.9,73.1',
            monthly_rainfall_csv='1.47,1.48,1.72,1.93,3.24,3.65,3.49,5.40,5.41,4.45,3.18,1.02',
            monthly_uv_csv='6.0,7.0,8.0,9.0,10.0,11.0,11.0,10.0,9.0,8.0,7.0,6.0',
            source_notes='Seeded Key West climate baseline from legacy platform; workbook should supersede later.',
        )
        session.add(climate)
        session.flush()

    water = session.exec(select(WaterProfile).where(WaterProfile.name == 'FKAA Starting Profile')).first()
    if not water:
        water = WaterProfile(
            name='FKAA Starting Profile',
            source_system='FKAA',
            ph=9.0,
            total_alkalinity_ppm=50.0,
            calcium_hardness_ppm=86.0,
            tds_ppm=230.0,
            chloride_ppm=50.0,
            sodium_ppm=22.0,
            notes='Derived from public FKAA reports used as a starting water profile',
        )
        session.add(water)
        session.flush()

    if not session.exec(select(BaselineModelVersion)).first():
        coefficients = {
            'liquid_chlorine_12pct_gal': 0.00809,
            'muriatic_acid_gal': 0.00162,
            'sodium_bicarbonate_lb': 0.00192,
            'cyanuric_acid_lb': 0.0000615,
            'calcium_chloride_lb': 0.000576,
            'algaecide_oz': 0.002598,
            'phosphate_remover_oz': 0.000800,
            'chem_clean_express_oz': 0.000300,
        }
        residential_weights = {
            'liquid_chlorine_12pct_gal': {'bath': 0.40, 'debris': 0.25, 'filtration': 0.35, 'overflow': 0.10, 'backwash': 0.08},
            'muriatic_acid_gal': {'bath': 0.20, 'debris': 0.15, 'filtration': 0.25, 'overflow': 0.05, 'backwash': 0.04},
            'sodium_bicarbonate_lb': {'bath': 0.12, 'debris': 0.10, 'filtration': 0.22, 'overflow': 0.12, 'backwash': 0.14},
            'cyanuric_acid_lb': {'bath': 0.05, 'debris': 0.10, 'filtration': 0.05, 'overflow': 0.45, 'backwash': 0.45},
            'calcium_chloride_lb': {'bath': 0.05, 'debris': 0.05, 'filtration': 0.08, 'overflow': 0.30, 'backwash': 0.30},
            'algaecide_oz': {'bath': 0.15, 'debris': 0.45, 'filtration': 0.35, 'overflow': 0.03, 'backwash': 0.02},
            'phosphate_remover_oz': {'bath': 0.20, 'debris': 0.55, 'filtration': 0.25, 'overflow': 0.03, 'backwash': 0.02},
            'chem_clean_express_oz': {'bath': 0.10, 'debris': 0.20, 'filtration': 0.25, 'overflow': 0.05, 'backwash': 0.05},
        }
        commercial_weights = {key: {k: round(v * 1.2, 4) for k, v in values.items()} for key, values in residential_weights.items()}
        session.add(BaselineModelVersion(
            model_family='residential',
            version_name='residential_v1',
            description='Residential baseline model with FKAA and Key West starting assumptions',
            climate_profile_id=climate.id,
            water_profile_id=water.id,
            coefficients_json=dumps(coefficients),
            weights_json=dumps(residential_weights),
        ))
        session.add(BaselineModelVersion(
            model_family='commercial',
            version_name='commercial_v1',
            description='Commercial baseline model with stronger condition weighting and same source profiles',
            climate_profile_id=climate.id,
            water_profile_id=water.id,
            coefficients_json=dumps(coefficients),
            weights_json=dumps(commercial_weights),
        ))

    for slug, display_name, category in DEFAULT_SOURCE_SYSTEMS:
        if not session.exec(select(SourceSystem).where(SourceSystem.slug == slug)).first():
            session.add(SourceSystem(slug=slug, display_name=display_name, category=category))

    session.commit()
    set_setting(session, 'labor_settings', DEFAULT_LABOR_SETTINGS, 'Default labor settings promoted from legacy estimator and intended to become admin-managed.')
    ensure_quote_workflow_settings(session)
    seed_tools(session)
