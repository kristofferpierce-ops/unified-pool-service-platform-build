"""Vendor identity resolution -- the supplier analog of ``customer_matching``.

Mirrors ``resolve_customer`` one-for-one (same never-orphan, flag-duplicates
policy, same O(1) short-circuit) with two deliberate, data-driven differences:

  * TAX-ID is Pass 1. A matching EIN/SSN is near-certain identity (customers have
    no tax-id). It is matched on a keyed hash, never plaintext.
  * NAME-ONLY matches DO NOT auto-merge (``VENDOR_STRONG_NAME_AUTOLINKS=False``).
    In the real vendor data name is the only signal and there are genuine >=0.90
    false-positive pairs (e.g. "City of Key West" vs "Kia of Key West"); an
    uncorroborated strong-name hit is flagged for review, not silently merged.
    Flip the flag to True for future sources that carry corroborating keys.

Built as parallel tables/services; the live customer code is untouched.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime
from difflib import SequenceMatcher

from sqlmodel import Session, select

from app.core.secrets import keyed_hash, norm_sensitive
from app.models.vendor_tables import Vendor, VendorMatch, VendorProfile

STRONG_NAME = 0.90
SUGGEST_NAME = 0.60
VENDOR_STRONG_NAME_AUTOLINKS = False   # see module docstring

# Legal-suffix / stop tokens dropped from the name key so "Pool Supply",
# "Pool Supply LLC" and "The Pool Supply" collapse and surface each other.
_STOP_TOKENS = {'inc', 'llc', 'co', 'corp', 'company', 'ltd', 'pa', 'cpa', 'the', 'lp', 'pllc'}


def norm_email(value: str) -> str:
    return (value or '').strip().lower()


def norm_phone(value: str) -> str:
    digits = re.sub(r'\D', '', value or '')
    return digits[-10:] if len(digits) > 10 else digits


def norm_taxid(value: str) -> str:
    return re.sub(r'\D', '', value or '')


def hash_taxid(raw: str) -> str:
    n = norm_sensitive(raw)
    return keyed_hash(n) if n else ''


def _vendor_name_key(value: str) -> str:
    v = re.sub(r'[^a-z0-9 ]', ' ', (value or '').lower())
    tokens = [t for t in v.split() if t and t not in _STOP_TOKENS]
    return ' '.join(tokens).strip()


def _similarity(a: str, b: str) -> float:
    a, b = _vendor_name_key(a), _vendor_name_key(b)
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a, b).ratio()


@dataclass
class VendorMatchResult:
    vendor_id: int | None
    status: str          # auto | flagged | suggested | unmatched | confirmed
    match_pass: int
    confidence: float
    created_vendor: bool
    candidates: list


def _profiles(session: Session) -> list[VendorProfile]:
    return list(session.exec(select(VendorProfile)).all())


def _vendor_display(p: VendorProfile) -> str:
    return p.company_name or p.display_name or p.person_name or f'Vendor {p.vendor_id}'


def _upsert_match(session: Session, source: str, external_id: str, *, name: str, email: str, phone: str,
                  company: str, tax_id_hash: str, vendor_id: int | None, status: str, match_pass: int,
                  confidence: float, candidates: list) -> VendorMatch:
    row = session.exec(
        select(VendorMatch).where(VendorMatch.source_slug == source).where(VendorMatch.external_id == external_id)
    ).first()
    if not row:
        row = VendorMatch(source_slug=source, external_id=external_id)
        session.add(row)
    row.external_name = name
    row.external_email = email
    row.external_phone = phone
    row.external_company = company
    row.external_tax_id_hash = tax_id_hash
    row.vendor_id = vendor_id
    row.status = status
    row.match_pass = match_pass
    row.confidence = confidence
    row.candidates_json = json.dumps(candidates)
    row.updated_at = datetime.utcnow()
    session.commit()
    session.refresh(row)
    return row


def _create_vendor(session: Session, *, source: str, name: str, company: str, person: str, display_name: str,
                   billing_name: str, address_block: str, notes: str, terms: str, vendor_type: str,
                   email: str, phone: str, tax_id_hash: str, tax_id_last4: str, is_active: bool,
                   is_1099: bool, artifact_id: int | None, row_id: int | None) -> Vendor:
    vendor = Vendor(vendor_type=vendor_type or 'supplier', name=(name or company or 'Vendor'),
                    billing_name=billing_name, notes=notes, address_block=address_block, is_active=is_active)
    session.add(vendor)
    session.commit()
    session.refresh(vendor)
    session.add(VendorProfile(
        vendor_id=vendor.id, display_name=(display_name or name), company_name=company, person_name=person,
        email=norm_email(email), phone=norm_phone(phone), tax_id_hash=tax_id_hash, tax_id_last4=tax_id_last4,
        terms=terms, is_1099=is_1099, is_active=is_active, primary_source=source,
        source_artifact_id=artifact_id, source_row_id=row_id,
    ))
    session.commit()
    return vendor


def _enrich_vendor_profile(session: Session, vendor_id: int, *, email: str, phone: str,
                           tax_id_hash: str, tax_id_last4: str) -> None:
    p = session.exec(select(VendorProfile).where(VendorProfile.vendor_id == vendor_id)).first()
    if not p:
        return
    changed = False
    if not p.email and email:
        p.email = norm_email(email); changed = True
    if not p.phone and phone:
        p.phone = norm_phone(phone); changed = True
    if not p.tax_id_hash and tax_id_hash:
        p.tax_id_hash = tax_id_hash; p.tax_id_last4 = tax_id_last4; changed = True
    if changed:
        p.updated_at = datetime.utcnow()
        session.commit()


def resolve_vendor(
    session: Session,
    *,
    source: str,
    external_id: str,
    name: str = '',
    company: str = '',
    person: str = '',
    display_name: str = '',
    billing_name: str = '',
    address_block: str = '',
    notes: str = '',
    terms: str = '',
    vendor_type: str = 'supplier',
    email: str = '',
    phone: str = '',
    tax_id: str = '',
    tax_id_hash: str = '',
    tax_id_last4: str = '',
    is_active: bool = True,
    is_1099: bool = False,
    artifact_id: int | None = None,
    row_id: int | None = None,
    auto_create_when_new: bool = True,
) -> VendorMatchResult:
    """Resolve an external vendor record to an internal Vendor via tax-id -> email
    -> phone -> fuzzy-name passes, never orphaning (mirrors resolve_customer)."""
    prior = session.exec(
        select(VendorMatch).where(VendorMatch.source_slug == source).where(VendorMatch.external_id == external_id)
    ).first()
    if prior and prior.vendor_id:
        return VendorMatchResult(prior.vendor_id, prior.status, prior.match_pass, prior.confidence, False,
                                 json.loads(prior.candidates_json or '[]'))

    if tax_id and not tax_id_hash:
        tax_id_hash = hash_taxid(tax_id)
        tax_id_last4 = norm_sensitive(tax_id)[-4:]

    nt, ne, np = tax_id_hash, norm_email(email), norm_phone(phone)
    profiles = [p for p in _profiles(session) if p.is_active]   # HIDDEN excluded from auto-match

    create_kwargs = dict(source=source, name=name, company=company, person=person, display_name=display_name,
                         billing_name=billing_name, address_block=address_block, notes=notes, terms=terms,
                         vendor_type=vendor_type, email=email, phone=phone, tax_id_hash=tax_id_hash,
                         tax_id_last4=tax_id_last4, is_active=is_active, is_1099=is_1099,
                         artifact_id=artifact_id, row_id=row_id)

    def _link(p, status, mp, conf):
        _upsert_match(session, source, external_id, name=name, email=email, phone=phone, company=company,
                      tax_id_hash=nt, vendor_id=p.vendor_id, status=status, match_pass=mp,
                      confidence=conf, candidates=[])
        _enrich_vendor_profile(session, p.vendor_id, email=email, phone=phone,
                               tax_id_hash=nt, tax_id_last4=tax_id_last4)
        return VendorMatchResult(p.vendor_id, status, mp, conf, False, [])

    # Pass 1: exact tax-id.
    if nt:
        for p in profiles:
            if p.tax_id_hash and p.tax_id_hash == nt:
                return _link(p, 'auto', 1, 1.0)
    # Pass 2: exact email.
    if ne:
        for p in profiles:
            if p.email and p.email == ne:
                return _link(p, 'auto', 2, 0.97)
    # Pass 2: exact phone.
    if np:
        for p in profiles:
            if p.phone and p.phone == np:
                return _link(p, 'auto', 2, 0.95)

    # Pass 2: fuzzy name/company.
    scored = []
    for p in profiles:
        score = max(_similarity(name, _vendor_display(p)), _similarity(company, p.company_name))
        if score > 0:
            scored.append((score, p))
    scored.sort(key=lambda x: x[0], reverse=True)

    if VENDOR_STRONG_NAME_AUTOLINKS and scored and scored[0][0] >= STRONG_NAME:
        score, p = scored[0]
        return _link(p, 'auto', 2, round(score, 3))

    candidates = [{
        'vendor_id': p.vendor_id, 'name': _vendor_display(p),
        'score': round(score, 3), 'reason': 'name/company similarity',
    } for score, p in scored if score >= SUGGEST_NAME][:3]

    # Pass 3: never orphan. Attribute to its own new vendor, flagged as a possible
    # duplicate for optional review; or (auto_create off) leave in the manual queue.
    if candidates and auto_create_when_new:
        vendor = _create_vendor(session, **create_kwargs)
        _upsert_match(session, source, external_id, name=name, email=email, phone=phone, company=company,
                      tax_id_hash=nt, vendor_id=vendor.id, status='flagged', match_pass=3,
                      confidence=candidates[0]['score'], candidates=candidates)
        return VendorMatchResult(vendor.id, 'flagged', 3, candidates[0]['score'], True, candidates)

    if candidates:
        _upsert_match(session, source, external_id, name=name, email=email, phone=phone, company=company,
                      tax_id_hash=nt, vendor_id=None, status='suggested', match_pass=3,
                      confidence=candidates[0]['score'], candidates=candidates)
        return VendorMatchResult(None, 'suggested', 3, candidates[0]['score'], False, candidates)

    if auto_create_when_new:
        vendor = _create_vendor(session, **create_kwargs)
        _upsert_match(session, source, external_id, name=name, email=email, phone=phone, company=company,
                      tax_id_hash=nt, vendor_id=vendor.id, status='auto', match_pass=1, confidence=1.0, candidates=[])
        return VendorMatchResult(vendor.id, 'auto', 1, 1.0, True, [])

    _upsert_match(session, source, external_id, name=name, email=email, phone=phone, company=company,
                  tax_id_hash=nt, vendor_id=None, status='unmatched', match_pass=0, confidence=0.0, candidates=[])
    return VendorMatchResult(None, 'unmatched', 0, 0.0, False, [])


def confirm_match(session: Session, match_id: int, vendor_id: int) -> VendorMatch:
    row = session.get(VendorMatch, match_id)
    if not row:
        raise ValueError('Match not found')
    row.vendor_id = vendor_id
    row.status = 'confirmed'
    row.updated_at = datetime.utcnow()
    session.commit()
    session.refresh(row)
    return row


def unlink_match(session: Session, match_id: int) -> VendorMatch:
    row = session.get(VendorMatch, match_id)
    if not row:
        raise ValueError('Match not found')
    row.vendor_id = None
    row.status = 'unmatched'
    row.match_pass = 0
    row.updated_at = datetime.utcnow()
    session.commit()
    session.refresh(row)
    return row


def list_matches(session: Session, status: str | None = None, source: str | None = None) -> list[VendorMatch]:
    rows = list(session.exec(select(VendorMatch)).all())
    if status:
        rows = [r for r in rows if r.status == status]
    if source:
        rows = [r for r in rows if r.source_slug == source]
    rows.sort(key=lambda r: (r.status != 'suggested', r.status != 'unmatched', -(r.id or 0)))
    return rows


def merge_vendor(session: Session, from_vendor_id: int, into_vendor_id: int) -> None:
    """Merge a flagged possible-duplicate that really is the same vendor: re-point
    the additive cost FKs + id maps + match records to the target, then remove the
    now-empty vendor."""
    from app.models.asset_tables import AssetRecord
    from app.models.connector_tables import ExternalIdentityMap
    from app.models.tables import ChemicalProduct, CommercialVendorOrder, ProductPriceHistory

    if from_vendor_id == into_vendor_id:
        return
    for ph in session.exec(select(ProductPriceHistory).where(ProductPriceHistory.vendor_id == from_vendor_id)).all():
        ph.vendor_id = into_vendor_id
    for cp in session.exec(select(ChemicalProduct).where(ChemicalProduct.default_vendor_id == from_vendor_id)).all():
        cp.default_vendor_id = into_vendor_id
    for ar in session.exec(select(AssetRecord).where(AssetRecord.vendor_id == from_vendor_id)).all():
        ar.vendor_id = into_vendor_id
    for order in session.exec(select(CommercialVendorOrder).where(CommercialVendorOrder.vendor_id == from_vendor_id)).all():
        order.vendor_id = into_vendor_id
    for eim in session.exec(
        select(ExternalIdentityMap)
        .where(ExternalIdentityMap.internal_type == 'vendor')
        .where(ExternalIdentityMap.internal_id == str(from_vendor_id))
    ).all():
        eim.internal_id = str(into_vendor_id)
    for m in session.exec(select(VendorMatch).where(VendorMatch.vendor_id == from_vendor_id)).all():
        m.vendor_id = into_vendor_id
        m.status = 'confirmed'
        m.updated_at = datetime.utcnow()
    for prof in session.exec(select(VendorProfile).where(VendorProfile.vendor_id == from_vendor_id)).all():
        session.delete(prof)
    vendor = session.get(Vendor, from_vendor_id)
    if vendor:
        session.delete(vendor)
    session.commit()


def vendor_matching_summary(session: Session) -> dict:
    rows = list(session.exec(select(VendorMatch)).all())
    by_status: dict[str, int] = {}
    for r in rows:
        by_status[r.status] = by_status.get(r.status, 0) + 1
    return {
        'total': len(rows),
        'by_status': by_status,
        'needs_review': by_status.get('suggested', 0) + by_status.get('unmatched', 0),
        'possible_duplicates': by_status.get('flagged', 0),
        'vendors': len(list(session.exec(select(VendorProfile)).all())),
    }
