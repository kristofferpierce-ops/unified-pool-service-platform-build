"""Three-pass customer identity resolution across external systems.

resolve_customer() takes an external record (a Skimmer customer, a FreshBooks
client) and resolves it to an internal Account + CustomerProfile:

  Pass 1 (exact):    normalized email match  -> auto-link.
  Pass 2 (assisted): exact phone, or strong fuzzy name/company -> auto-link;
                     a plausible-but-weaker match -> 'suggested' (candidates, no
                     auto-link) for the manual queue.
  Pass 3 (manual):   no candidates and it's a new customer -> create a fresh
                     account (revenue- or ops-only customers are still real);
                     genuinely ambiguous ones stay 'suggested' for a human.

Every resolution is recorded as a CustomerMatch so it can be reviewed, and
confirm_match()/unlink_match() let a human override any decision at any time.
Once set, matches persist (low-churn client base), so this stays low-maintenance.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime
from difflib import SequenceMatcher

from sqlmodel import Session, select

from app.models.customer_tables import CustomerMatch, CustomerProfile
from app.models.tables import Account

# Tunable thresholds.
STRONG_NAME = 0.90   # >= this fuzzy name/company similarity auto-links
SUGGEST_NAME = 0.60  # >= this surfaces as a manual-review candidate


def norm_email(value: str) -> str:
    return (value or '').strip().lower()


def norm_phone(value: str) -> str:
    digits = re.sub(r'\D', '', value or '')
    # Compare on the last 10 digits so a +1 country code doesn't defeat a match.
    return digits[-10:] if len(digits) > 10 else digits


def _name_key(value: str) -> str:
    return re.sub(r'[^a-z0-9 ]', '', (value or '').lower()).strip()


def _similarity(a: str, b: str) -> float:
    a, b = _name_key(a), _name_key(b)
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a, b).ratio()


@dataclass
class MatchResult:
    account_id: int | None
    status: str          # auto | suggested | unmatched | confirmed
    match_pass: int
    confidence: float
    created_account: bool
    candidates: list      # [{account_id, name, score, reason}]


def _profiles(session: Session) -> list[CustomerProfile]:
    return list(session.exec(select(CustomerProfile)).all())


def _account_display(profile: CustomerProfile) -> str:
    return profile.company_name or profile.display_name or f'Account {profile.account_id}'


def _upsert_match(session: Session, source: str, external_id: str, *, name: str, email: str,
                  phone: str, company: str, account_id: int | None, status: str, match_pass: int,
                  confidence: float, candidates: list) -> CustomerMatch:
    row = session.exec(
        select(CustomerMatch)
        .where(CustomerMatch.source_slug == source)
        .where(CustomerMatch.external_id == external_id)
    ).first()
    if not row:
        row = CustomerMatch(source_slug=source, external_id=external_id)
        session.add(row)
    row.external_name = name
    row.external_email = email
    row.external_phone = phone
    row.external_company = company
    row.account_id = account_id
    row.status = status
    row.match_pass = match_pass
    row.confidence = confidence
    row.candidates_json = json.dumps(candidates)
    row.updated_at = datetime.utcnow()
    session.commit()
    session.refresh(row)
    return row


def _create_account(session: Session, *, source: str, name: str, email: str, phone: str, company: str) -> Account:
    account = Account(account_type='residential', name=(company or name or 'Customer'))
    session.add(account)
    session.commit()
    session.refresh(account)
    session.add(CustomerProfile(
        account_id=account.id, display_name=name, email=norm_email(email),
        phone=norm_phone(phone), company_name=company, primary_source=source,
    ))
    session.commit()
    return account


def _enrich_profile(session: Session, account_id: int, *, email: str, phone: str) -> None:
    profile = session.exec(select(CustomerProfile).where(CustomerProfile.account_id == account_id)).first()
    if not profile:
        return
    changed = False
    if not profile.email and email:
        profile.email = norm_email(email)
        changed = True
    if not profile.phone and phone:
        profile.phone = norm_phone(phone)
        changed = True
    if changed:
        profile.updated_at = datetime.utcnow()
        session.commit()


def resolve_customer(
    session: Session,
    *,
    source: str,
    external_id: str,
    name: str = '',
    email: str = '',
    phone: str = '',
    company: str = '',
    auto_create_when_new: bool = True,
) -> MatchResult:
    """Resolve an external customer record to an internal account via 3 passes."""
    # Respect a prior confirmed/overridden decision.
    prior = session.exec(
        select(CustomerMatch)
        .where(CustomerMatch.source_slug == source)
        .where(CustomerMatch.external_id == external_id)
    ).first()
    if prior and prior.status == 'confirmed' and prior.account_id:
        return MatchResult(prior.account_id, 'confirmed', prior.match_pass, prior.confidence, False,
                           json.loads(prior.candidates_json or '[]'))

    ne, np = norm_email(email), norm_phone(phone)
    profiles = _profiles(session)

    # Pass 1: exact email.
    if ne:
        for p in profiles:
            if p.email and p.email == ne:
                _upsert_match(session, source, external_id, name=name, email=email, phone=phone,
                              company=company, account_id=p.account_id, status='auto', match_pass=1,
                              confidence=1.0, candidates=[])
                _enrich_profile(session, p.account_id, email=email, phone=phone)
                return MatchResult(p.account_id, 'auto', 1, 1.0, False, [])

    # Pass 2: exact phone.
    if np:
        for p in profiles:
            if p.phone and p.phone == np:
                _upsert_match(session, source, external_id, name=name, email=email, phone=phone,
                              company=company, account_id=p.account_id, status='auto', match_pass=2,
                              confidence=0.95, candidates=[])
                _enrich_profile(session, p.account_id, email=email, phone=phone)
                return MatchResult(p.account_id, 'auto', 2, 0.95, False, [])

    # Pass 2: fuzzy name/company.
    scored = []
    for p in profiles:
        score = max(_similarity(name, _account_display(p)), _similarity(company, p.company_name))
        if score > 0:
            scored.append((score, p))
    scored.sort(key=lambda x: x[0], reverse=True)

    if scored and scored[0][0] >= STRONG_NAME:
        score, p = scored[0]
        _upsert_match(session, source, external_id, name=name, email=email, phone=phone,
                      company=company, account_id=p.account_id, status='auto', match_pass=2,
                      confidence=round(score, 3), candidates=[])
        _enrich_profile(session, p.account_id, email=email, phone=phone)
        return MatchResult(p.account_id, 'auto', 2, round(score, 3), False, [])

    candidates = [{
        'account_id': p.account_id, 'name': _account_display(p),
        'score': round(score, 3), 'reason': 'name/company similarity',
    } for score, p in scored if score >= SUGGEST_NAME][:3]

    # Pass 3: manual queue vs new account.
    if candidates:
        _upsert_match(session, source, external_id, name=name, email=email, phone=phone,
                      company=company, account_id=None, status='suggested', match_pass=3,
                      confidence=candidates[0]['score'], candidates=candidates)
        return MatchResult(None, 'suggested', 3, candidates[0]['score'], False, candidates)

    if auto_create_when_new:
        account = _create_account(session, source=source, name=name, email=email, phone=phone, company=company)
        _upsert_match(session, source, external_id, name=name, email=email, phone=phone,
                      company=company, account_id=account.id, status='auto', match_pass=1,
                      confidence=1.0, candidates=[])
        return MatchResult(account.id, 'auto', 1, 1.0, True, [])

    _upsert_match(session, source, external_id, name=name, email=email, phone=phone,
                  company=company, account_id=None, status='unmatched', match_pass=0,
                  confidence=0.0, candidates=[])
    return MatchResult(None, 'unmatched', 0, 0.0, False, [])


def confirm_match(session: Session, match_id: int, account_id: int) -> CustomerMatch:
    """Manually link (or override) a match to a specific account."""
    row = session.get(CustomerMatch, match_id)
    if not row:
        raise ValueError('Match not found')
    row.account_id = account_id
    row.status = 'confirmed'
    row.updated_at = datetime.utcnow()
    session.commit()
    session.refresh(row)
    return row


def unlink_match(session: Session, match_id: int) -> CustomerMatch:
    """Clear a match's account link and re-queue it for review."""
    row = session.get(CustomerMatch, match_id)
    if not row:
        raise ValueError('Match not found')
    row.account_id = None
    row.status = 'unmatched'
    row.match_pass = 0
    row.updated_at = datetime.utcnow()
    session.commit()
    session.refresh(row)
    return row


def list_matches(session: Session, status: str | None = None, source: str | None = None) -> list[CustomerMatch]:
    rows = list(session.exec(select(CustomerMatch)).all())
    if status:
        rows = [r for r in rows if r.status == status]
    if source:
        rows = [r for r in rows if r.source_slug == source]
    rows.sort(key=lambda r: (r.status != 'suggested', r.status != 'unmatched', -(r.id or 0)))
    return rows


def matching_summary(session: Session) -> dict:
    rows = list(session.exec(select(CustomerMatch)).all())
    by_status: dict[str, int] = {}
    for r in rows:
        by_status[r.status] = by_status.get(r.status, 0) + 1
    return {
        'total': len(rows),
        'by_status': by_status,
        'needs_review': by_status.get('suggested', 0) + by_status.get('unmatched', 0),
        'accounts': len(list(session.exec(select(CustomerProfile)).all())),
    }
