from __future__ import annotations

from typing import Any, Iterable, Optional

from sqlmodel import Session, select

from app.models.tables import (
    BaselineModelVersion,
    ChemicalCatalog,
    ChemicalCoefficient,
    ChemicalWeight,
    ClimateProfile,
    CompanyExpense,
    EstimateRun,
    FieldObservation,
    Property,
    SystemSetting,
    WaterProfile,
)


def get_all(session: Session, model: Any) -> list[Any]:
    return list(session.exec(select(model)).all())


def get_system_settings(session: Session) -> dict[str, Any]:
    rows = session.exec(select(SystemSetting)).all()
    return {row.key: row.value for row in rows}


def upsert_system_setting(session: Session, key: str, value: Any, description: str = "") -> SystemSetting:
    row = session.exec(select(SystemSetting).where(SystemSetting.key == key)).first()
    if row is None:
        row = SystemSetting(key=key, value=value, description=description)
        session.add(row)
    else:
        row.value = value
        if description:
            row.description = description
    session.commit()
    session.refresh(row)
    return row


def get_active_baseline_model(session: Session, pool_type: str = "residential") -> Optional[BaselineModelVersion]:
    return session.exec(
        select(BaselineModelVersion)
        .where(BaselineModelVersion.pool_type == pool_type)
        .where(BaselineModelVersion.active == True)  # noqa: E712
        .order_by(BaselineModelVersion.created_at.desc())
    ).first()


def get_model_coefficients(session: Session, model_version_id: int) -> dict[str, float]:
    rows = session.exec(select(ChemicalCoefficient).where(ChemicalCoefficient.model_version_id == model_version_id)).all()
    return {row.chemical_key: row.annual_coefficient_per_pool_gallon for row in rows}


def get_model_weights(session: Session, model_version_id: int) -> dict[str, dict[str, float]]:
    rows = session.exec(select(ChemicalWeight).where(ChemicalWeight.model_version_id == model_version_id)).all()
    return {
        row.chemical_key: {
            "bath": row.bath_weight,
            "debris": row.debris_weight,
            "filtration": row.filtration_weight,
            "overflow": row.overflow_weight,
            "backwash": row.backwash_weight,
        }
        for row in rows
    }


def get_chemical_catalog(session: Session) -> list[ChemicalCatalog]:
    return list(session.exec(select(ChemicalCatalog).where(ChemicalCatalog.active == True)).all())  # noqa: E712


def get_property(session: Session, property_id: int) -> Optional[Property]:
    return session.get(Property, property_id)


def get_estimate_runs_for_property(session: Session, property_id: int) -> list[EstimateRun]:
    return list(
        session.exec(
            select(EstimateRun).where(EstimateRun.property_id == property_id).order_by(EstimateRun.created_at.desc())
        ).all()
    )


def get_observations_for_property(session: Session, property_id: int) -> list[FieldObservation]:
    return list(
        session.exec(
            select(FieldObservation)
            .where(FieldObservation.property_id == property_id)
            .order_by(FieldObservation.observed_on.desc())
        ).all()
    )
