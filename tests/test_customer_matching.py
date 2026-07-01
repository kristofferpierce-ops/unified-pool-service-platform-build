"""Locks the 3-pass customer matching: exact, assisted, manual, override."""
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

import app.models  # noqa: F401
from app.models.customer_tables import CustomerProfile
from app.models.tables import Account
from app.services.customer_matching import (
    confirm_match,
    list_matches,
    resolve_customer,
    unlink_match,
)


def _session() -> Session:
    engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
    SQLModel.metadata.create_all(engine)
    return Session(engine)


def _seed_skimmer_customer(session, name, email='', phone='', company='', ext='sk-1'):
    return resolve_customer(session, source='skimmer', external_id=ext, name=name,
                            email=email, phone=phone, company=company)


def test_pass1_exact_email_autolinks():
    with _session() as s:
        seed = _seed_skimmer_customer(s, 'Mateo Alvarez', email='mateo@example.com', ext='sk-1')
        assert seed.created_account and seed.account_id

        # FreshBooks client with the same email -> pass 1 auto-link to the same account.
        fb = resolve_customer(s, source='freshbooks', external_id='fb-1',
                              name='M. Alvarez', email='MATEO@example.com')
        assert fb.status == 'auto'
        assert fb.match_pass == 1
        assert fb.account_id == seed.account_id
        assert not fb.created_account
        # No duplicate account created.
        assert len(list(s.exec(select(Account)).all())) == 1


def test_pass2_exact_phone_autolinks():
    with _session() as s:
        seed = _seed_skimmer_customer(s, 'Sunset Resort', phone='+1 (305) 555-1302', ext='sk-2')
        fb = resolve_customer(s, source='freshbooks', external_id='fb-2',
                              name='Totally Different Name', phone='3055551302')
        assert fb.status == 'auto'
        assert fb.match_pass == 2
        assert fb.account_id == seed.account_id


def test_pass3_ambiguous_name_goes_to_manual_queue():
    with _session() as s:
        seed = _seed_skimmer_customer(s, 'Oceanview Pools LLC', company='Oceanview Pools LLC', ext='sk-3')
        # Similar name, no email/phone -> suggested (manual), not auto-linked.
        fb = resolve_customer(s, source='freshbooks', external_id='fb-3',
                              name='Oceanview Pool', company='Oceanview Pool')
        assert fb.status == 'suggested'
        assert fb.match_pass == 3
        assert fb.account_id is None
        assert fb.candidates and fb.candidates[0]['account_id'] == seed.account_id


def test_new_customer_with_no_match_creates_account():
    with _session() as s:
        _seed_skimmer_customer(s, 'Existing Person', email='a@a.com', ext='sk-4')
        fb = resolve_customer(s, source='freshbooks', external_id='fb-4',
                              name='Brand New Client', email='new@client.com')
        assert fb.status == 'auto'
        assert fb.created_account
        assert len(list(s.exec(select(Account)).all())) == 2


def test_manual_confirm_and_override_persists():
    with _session() as s:
        seed = _seed_skimmer_customer(s, 'Oceanview Pools LLC', company='Oceanview Pools LLC', ext='sk-5')
        fb = resolve_customer(s, source='freshbooks', external_id='fb-5',
                              name='Oceanview Pool', company='Oceanview Pool')
        assert fb.status == 'suggested'

        match = [m for m in list_matches(s, source='freshbooks') if m.external_id == 'fb-5'][0]
        confirm_match(s, match.id, seed.account_id)

        # Re-resolving respects the confirmed decision (does not re-queue).
        again = resolve_customer(s, source='freshbooks', external_id='fb-5',
                                 name='Oceanview Pool', company='Oceanview Pool')
        assert again.status == 'confirmed'
        assert again.account_id == seed.account_id

        # Override / unlink re-queues it.
        unlink_match(s, match.id)
        remaining = [m for m in list_matches(s, source='freshbooks') if m.external_id == 'fb-5'][0]
        assert remaining.account_id is None and remaining.status == 'unmatched'
