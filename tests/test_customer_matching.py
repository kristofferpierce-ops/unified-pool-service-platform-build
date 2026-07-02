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


def test_pass3_ambiguous_gets_own_account_and_flag():
    with _session() as s:
        seed = _seed_skimmer_customer(s, 'Oceanview Pools LLC', company='Oceanview Pools LLC', ext='sk-3')
        # Similar name, no email/phone -> auto-attributed to its OWN account, but
        # flagged as a possible duplicate (never orphaned).
        fb = resolve_customer(s, source='freshbooks', external_id='fb-3',
                              name='Oceanview Pool', company='Oceanview Pool')
        assert fb.status == 'flagged'
        assert fb.match_pass == 3
        assert fb.account_id is not None and fb.account_id != seed.account_id
        assert fb.created_account
        assert fb.candidates and fb.candidates[0]['account_id'] == seed.account_id
        assert len(list(s.exec(select(Account)).all())) == 2


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
        assert fb.status == 'flagged'

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


def test_merge_account_moves_billing_and_removes_source():
    from app.models.ops_tables import BillingDocument
    from app.services.customer_matching import matching_summary, merge_account
    with _session() as s:
        seed = _seed_skimmer_customer(s, 'Oceanview Pools LLC', company='Oceanview Pools LLC', ext='sk-9')
        fb = resolve_customer(s, source='freshbooks', external_id='fb-9',
                              name='Oceanview Pool', company='Oceanview Pool')
        assert fb.status == 'flagged'
        assert matching_summary(s)['possible_duplicates'] == 1

        # A billing doc on the flagged (own) account.
        s.add(BillingDocument(source_slug='freshbooks', external_id='inv-x',
                              account_id=fb.account_id, total_amount=100.0))
        s.commit()

        merge_account(s, fb.account_id, seed.account_id)

        docs = list(s.exec(select(BillingDocument)).all())
        assert docs and all(d.account_id == seed.account_id for d in docs)  # revenue moved
        assert s.get(Account, fb.account_id) is None                        # source account removed
        assert matching_summary(s)['possible_duplicates'] == 0              # flag resolved
