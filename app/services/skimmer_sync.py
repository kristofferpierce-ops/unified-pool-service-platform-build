"""Skimmer ingestion: pull -> raw -> normalized -> applied into the ops tables.

Flows Skimmer's field-ops data through the platform's connector pipeline:
  - customers / service_locations / bodies_of_water / work_orders / routes are
    captured as RawSourceRecord + NormalizedSourceRecord (the raw/normalized
    ledger), then
  - service_locations become Properties, bodies_of_water become PoolVessels, and
    work_orders become ServiceVisits with ActualLaborFact / ActualChemicalFact /
    TechnicianAssignment -- the actuals that route P&L and the expected-vs-actual
    variance engine read.

Idempotent: re-syncing skips already-ingested records (by external id) and never
duplicates a property, vessel, or service visit.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, time

from sqlmodel import Session, select

from app.connectors.skimmer.client import SkimmerClient, get_skimmer_client
from app.connectors.skimmer.normalizer import (
    normalize_body_of_water,
    normalize_customer,
    normalize_route,
    normalize_service_location,
    normalize_work_order,
)
from app.models.connector_tables import (
    ConnectorRun,
    ExternalIdentityMap,
    NormalizedSourceRecord,
    RawSourceRecord,
)
from app.models.ops_tables import (
    ActualChemicalFact,
    ActualLaborFact,
    ServiceVisit,
    TechnicianAssignment,
)
from app.models.tables import Account, ChemicalProduct, PoolVessel, Property

SOURCE = 'skimmer'


@dataclass
class SkimmerSyncResult:
    mode: str
    raw_records_new: int = 0
    normalized_records_new: int = 0
    properties_created: int = 0
    vessels_created: int = 0
    service_visits_created: int = 0
    chemical_facts_created: int = 0
    unmatched_work_orders: int = 0
    run_id: int | None = None


def _hash(payload: dict) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()


def _map_get(session: Session, entity_type: str, external_id: str) -> str | None:
    row = session.exec(
        select(ExternalIdentityMap)
        .where(ExternalIdentityMap.source_slug == SOURCE)
        .where(ExternalIdentityMap.entity_type == entity_type)
        .where(ExternalIdentityMap.external_id == external_id)
    ).first()
    return row.internal_id if row else None


def _map_set(session: Session, entity_type: str, external_id: str, internal_type: str, internal_id: int) -> None:
    session.add(ExternalIdentityMap(
        source_slug=SOURCE, entity_type=entity_type, external_id=external_id,
        internal_type=internal_type, internal_id=str(internal_id),
    ))


def _persist_ledger(session: Session, run: ConnectorRun, record_type: str, raw_items: list[dict], normalizer) -> tuple[list[dict], int, int]:
    """Write raw + normalized rows (deduped by external id). Return (normalized_dicts, new_raw, new_norm)."""
    normalized_dicts: list[dict] = []
    new_raw = new_norm = 0
    for raw_item in raw_items:
        norm = normalizer(raw_item)
        external_id = norm.get('external_id', '')
        normalized_dicts.append(norm)
        exists = session.exec(
            select(RawSourceRecord)
            .where(RawSourceRecord.source_slug == SOURCE)
            .where(RawSourceRecord.record_type == record_type)
            .where(RawSourceRecord.external_id == external_id)
        ).first()
        if exists:
            continue
        raw = RawSourceRecord(
            source_slug=SOURCE, connector_run_id=run.id, external_id=external_id,
            record_type=record_type, payload_json=json.dumps(raw_item, default=str),
            payload_hash=_hash(raw_item), status='raw',
        )
        session.add(raw)
        session.commit()
        session.refresh(raw)
        new_raw += 1
        session.add(NormalizedSourceRecord(
            raw_record_id=raw.id, source_slug=SOURCE, entity_type=record_type,
            normalized_json=json.dumps(norm, default=str), fingerprint=external_id,
        ))
        new_norm += 1
    session.commit()
    return normalized_dicts, new_raw, new_norm


def _ensure_import_account(session: Session) -> Account:
    account = session.exec(select(Account).where(Account.name == 'Skimmer Import')).first()
    if not account:
        account = Account(account_type='imported', name='Skimmer Import',
                          notes='Auto-created to hold properties imported from Skimmer.')
        session.add(account)
        session.commit()
        session.refresh(account)
    return account


def _chemical_index(session: Session) -> list[tuple[int, str]]:
    index: list[tuple[int, str]] = []
    for p in session.exec(select(ChemicalProduct)).all():
        labels = [p.name, p.sku] + [a.strip() for a in (p.aliases_csv or '').split(',') if a.strip()]
        for label in labels:
            index.append((p.id, label.lower()))
    return index


def _match_chemical(name: str, index: list[tuple[int, str]]) -> int | None:
    n = name.lower().strip()
    if not n:
        return None
    for pid, label in index:
        if label and (label in n or n in label):
            return pid
    return None


def sync_skimmer(session: Session, client: SkimmerClient | None = None, apply: bool = True) -> SkimmerSyncResult:
    client = client or get_skimmer_client()
    result = SkimmerSyncResult(mode=client.mode)

    run = ConnectorRun(source_slug=SOURCE, run_type='pull', direction='inbound', status='running')
    session.add(run)
    session.commit()
    session.refresh(run)
    result.run_id = run.id

    # --- raw + normalized ledger for every entity type ---
    customers, r1, n1 = _persist_ledger(session, run, 'customer', client.customers(), normalize_customer)
    locations, r2, n2 = _persist_ledger(session, run, 'service_location', client.service_locations(), normalize_service_location)
    waters, r3, n3 = _persist_ledger(session, run, 'body_of_water', client.bodies_of_water(), normalize_body_of_water)
    work_orders, r4, n4 = _persist_ledger(session, run, 'work_order', client.work_orders(), normalize_work_order)
    routes, r5, n5 = _persist_ledger(session, run, 'route', client.routes(), normalize_route)
    result.raw_records_new = r1 + r2 + r3 + r4 + r5
    result.normalized_records_new = n1 + n2 + n3 + n4 + n5

    if apply:
        account = _ensure_import_account(session)
        chem_index = _chemical_index(session)

        # service_location -> Property
        for sl in locations:
            ext = sl['external_id']
            if _map_get(session, 'service_location', ext):
                continue
            prop = Property(
                account_id=account.id, name=sl['name'] or ext,
                address_line_1=sl['address'], city=sl['city'], state=sl['state'],
                postal_code=sl['zip'], latitude=sl['latitude'], longitude=sl['longitude'],
                account_type='residential',
            )
            session.add(prop)
            session.commit()
            session.refresh(prop)
            _map_set(session, 'service_location', ext, 'property', prop.id)
            session.commit()
            result.properties_created += 1

        # body_of_water -> PoolVessel
        for bow in waters:
            ext = bow['external_id']
            if _map_get(session, 'body_of_water', ext):
                continue
            prop_id = _map_get(session, 'service_location', bow['service_location_external_id'])
            if not prop_id:
                continue
            vessel = PoolVessel(property_id=int(prop_id), name=bow['name'], gallons=bow['gallons'])
            session.add(vessel)
            session.commit()
            session.refresh(vessel)
            _map_set(session, 'body_of_water', ext, 'pool_vessel', vessel.id)
            session.commit()
            result.vessels_created += 1

        # work_order -> ServiceVisit + actuals
        for wo in work_orders:
            ext = wo['external_id']
            prop_id = _map_get(session, 'service_location', wo['service_location_external_id'])
            if not prop_id:
                result.unmatched_work_orders += 1
                continue
            existing = session.exec(
                select(ServiceVisit)
                .where(ServiceVisit.source_slug == SOURCE)
                .where(ServiceVisit.external_id == ext)
            ).first()
            if existing:
                continue
            occurred = datetime.combine(wo['service_date'], time.min) if wo['service_date'] else datetime.utcnow()
            visit = ServiceVisit(
                property_id=int(prop_id), source_slug=SOURCE, external_id=ext,
                occurred_at=occurred, status='completed', notes=wo['work_needed'],
            )
            session.add(visit)
            session.commit()
            session.refresh(visit)
            result.service_visits_created += 1

            session.add(ActualLaborFact(
                service_visit_id=visit.id, total_minutes=wo['actual_minutes'],
                drive_minutes=0.0, tech_count=1,
            ))
            if wo['technician']:
                session.add(TechnicianAssignment(
                    service_visit_id=visit.id, technician_name=wo['technician'],
                    assigned_minutes=wo['actual_minutes'],
                ))
            for chem in wo['chemicals']:
                session.add(ActualChemicalFact(
                    service_visit_id=visit.id,
                    chemical_product_id=_match_chemical(chem['name'], chem_index),
                    chemical_name=chem['name'], quantity=chem['quantity'], unit=chem['unit'],
                ))
                result.chemical_facts_created += 1
            session.commit()

    run.status = 'completed'
    run.finished_at = datetime.utcnow()
    run.raw_record_count = result.raw_records_new
    run.normalized_record_count = result.normalized_records_new
    run.applied_count = result.service_visits_created
    run.notes = f'mode={result.mode}'
    session.commit()
    return result
