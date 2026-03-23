from __future__ import annotations

from sqlmodel import Session, select

from app.models.tables import (
    BaselineModelVersion,
    ChemicalCatalog,
    ChemicalCoefficient,
    ChemicalWeight,
    ClimateProfile,
    CompanyExpense,
    SystemSetting,
    WaterProfile,
)
from app.services.seeds import (
    DEFAULT_BASELINE_MODEL,
    DEFAULT_CHEMICALS,
    DEFAULT_CHEMICAL_COEFFICIENTS,
    DEFAULT_CHEMICAL_WEIGHTS,
    DEFAULT_CLIMATE_PROFILE,
    DEFAULT_COMPANY_EXPENSES,
    DEFAULT_SYSTEM_SETTINGS,
    DEFAULT_WATER_PROFILE,
)


def seed_defaults(session: Session) -> None:
    if session.exec(select(SystemSetting)).first() is None:
        for key, payload in DEFAULT_SYSTEM_SETTINGS.items():
            session.add(SystemSetting(key=key, value=payload["value"], description=payload["description"]))

    if session.exec(select(CompanyExpense)).first() is None:
        for category, items in DEFAULT_COMPANY_EXPENSES.items():
            for expense_name, annual_cost in items.items():
                session.add(CompanyExpense(category=category, expense_name=expense_name, annual_cost=annual_cost))

    if session.exec(select(ChemicalCatalog)).first() is None:
        for key, payload in DEFAULT_CHEMICALS.items():
            session.add(
                ChemicalCatalog(
                    key=key,
                    display_name=payload["display_name"],
                    unit_name=payload["unit_name"],
                    default_unit_cost=payload["unit_cost"],
                    active=True,
                )
            )

    water_profile = session.exec(select(WaterProfile).where(WaterProfile.name == DEFAULT_WATER_PROFILE["name"])).first()
    if water_profile is None:
        water_profile = WaterProfile(**DEFAULT_WATER_PROFILE)
        session.add(water_profile)
        session.flush()

    climate_profile = session.exec(select(ClimateProfile).where(ClimateProfile.name == DEFAULT_CLIMATE_PROFILE["name"])).first()
    if climate_profile is None:
        climate_profile = ClimateProfile(**DEFAULT_CLIMATE_PROFILE)
        session.add(climate_profile)
        session.flush()

    model = session.exec(select(BaselineModelVersion).where(BaselineModelVersion.name == DEFAULT_BASELINE_MODEL["name"])).first()
    if model is None:
        model = BaselineModelVersion(
            **DEFAULT_BASELINE_MODEL,
            climate_profile_id=climate_profile.id,
            water_profile_id=water_profile.id,
        )
        session.add(model)
        session.flush()

        for chemical_key, coefficient in DEFAULT_CHEMICAL_COEFFICIENTS.items():
            session.add(
                ChemicalCoefficient(
                    model_version_id=model.id,
                    chemical_key=chemical_key,
                    annual_coefficient_per_pool_gallon=coefficient,
                )
            )
        for chemical_key, weights in DEFAULT_CHEMICAL_WEIGHTS.items():
            session.add(
                ChemicalWeight(
                    model_version_id=model.id,
                    chemical_key=chemical_key,
                    bath_weight=weights["bath"],
                    debris_weight=weights["debris"],
                    filtration_weight=weights["filtration"],
                    overflow_weight=weights["overflow"],
                    backwash_weight=weights["backwash"],
                )
            )

    session.commit()
