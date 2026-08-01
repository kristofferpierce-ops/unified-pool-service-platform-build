"""Vendor identity resolution: tax-id Pass 1, never-orphan, name-only flags (not merges)."""
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

import app.models  # noqa: F401
from app.models.tables import ProductPriceHistory
from app.models.vendor_tables import Vendor, VendorProfile
from app.services.vendor_matching import (
    confirm_match, list_matches, merge_vendor, resolve_vendor, unlink_match, vendor_matching_summary,
)


def _session() -> Session:
    engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
    SQLModel.metadata.create_all(engine)
    return Session(engine)


def _count(s, model):
    return len(s.exec(select(model)).all())


def test_pass1_exact_taxid_autolinks():
    with _session() as s:
        resolve_vendor(s, source='qb', external_id='v1', name='Poolcorp Inc', tax_id='12-3456789')
        r = resolve_vendor(s, source='qb', external_id='v2', name='POOLCORP', tax_id='123456789')  # same EIN, diff name
        assert r.status == 'auto' and r.match_pass == 1
        assert _count(s, Vendor) == 1   # deduped by tax-id, no duplicate


def test_pass2_exact_email_autolinks():
    with _session() as s:
        resolve_vendor(s, source='qb', external_id='v1', name='SCP', email='sales@scp.com')
        r = resolve_vendor(s, source='qb', external_id='v2', name='SCP Distributors', email='SALES@scp.com')
        assert r.status == 'auto' and r.match_pass == 2
        assert _count(s, Vendor) == 1


def test_name_only_match_flags_not_merges():
    # The vendor divergence: an uncorroborated strong-name match must NOT auto-merge.
    with _session() as s:
        seed = resolve_vendor(s, source='qb', external_id='v1', name='Premier Painting')
        r = resolve_vendor(s, source='qb', external_id='v2', name='Premier Paitning')  # typo, no other key
        assert r.status == 'flagged' and r.match_pass == 3
        assert r.vendor_id != seed.vendor_id           # its OWN vendor, not merged
        assert r.candidates and r.candidates[0]['vendor_id'] == seed.vendor_id
        assert _count(s, Vendor) == 2


def test_false_positive_names_stay_distinct():
    with _session() as s:
        a = resolve_vendor(s, source='qb', external_id='v1', name='City of Key West')
        b = resolve_vendor(s, source='qb', external_id='v2', name='Kia of Key West')
        assert a.vendor_id != b.vendor_id              # never silently collapsed


def test_new_vendor_no_match_creates():
    with _session() as s:
        r = resolve_vendor(s, source='qb', external_id='v1', name='Brand New Supply')
        assert r.status == 'auto' and r.created_vendor is True and r.vendor_id


def test_short_circuit_on_prior_map():
    with _session() as s:
        first = resolve_vendor(s, source='qb', external_id='v1', name='SCP')
        again = resolve_vendor(s, source='qb', external_id='v1', name='TOTALLY DIFFERENT')  # same source+ext id
        assert again.vendor_id == first.vendor_id and again.created_vendor is False


def test_hidden_vendor_excluded_from_automatch():
    with _session() as s:
        resolve_vendor(s, source='qb', external_id='v1', name='Ace Pool Supply', is_active=False)
        r = resolve_vendor(s, source='qb', external_id='v2', name='Ace Pool Supply')  # exact name
        assert r.vendor_id != 1 or r.status != 'auto'  # inactive not a candidate -> new vendor
        assert _count(s, Vendor) == 2


def test_taxid_stored_as_hash_not_plaintext():
    with _session() as s:
        resolve_vendor(s, source='qb', external_id='v1', name='Poolcorp', tax_id='12-3456789')
        p = s.exec(select(VendorProfile)).first()
        assert p.tax_id_hash and p.tax_id_hash != '123456789' and p.tax_id_hash != '12-3456789'
        assert p.tax_id_last4 == '6789'
        # no attribute on the profile ever holds the plaintext tax id
        assert '123456789' not in ' '.join(str(v) for v in vars(p).values())


def test_confirm_and_unlink():
    with _session() as s:
        resolve_vendor(s, source='qb', external_id='v1', name='Ace Pool Supply')
        # same name but auto-create off -> a strong candidate held in the manual queue
        r2 = resolve_vendor(s, source='qb', external_id='v2', name='Ace Pool Supply', auto_create_when_new=False)
        assert r2.status == 'suggested'
        matches = list_matches(s, status='suggested')
        confirm_match(s, matches[0].id, vendor_id=1)
        assert s.get(type(matches[0]), matches[0].id).status == 'confirmed'
        unlink_match(s, matches[0].id)
        assert s.get(type(matches[0]), matches[0].id).status == 'unmatched'


def test_merge_vendor_repoints_cost_fk_and_removes_source():
    with _session() as s:
        a = resolve_vendor(s, source='qb', external_id='v1', name='Premier Painting')
        b = resolve_vendor(s, source='qb', external_id='v2', name='Premier Paitning')  # flagged dup
        s.add(ProductPriceHistory(product_id=1, vendor_id=b.vendor_id, unit_cost=5.0)); s.commit()
        assert vendor_matching_summary(s)['possible_duplicates'] == 1
        merge_vendor(s, from_vendor_id=b.vendor_id, into_vendor_id=a.vendor_id)
        assert _count(s, Vendor) == 1
        ph = s.exec(select(ProductPriceHistory)).first()
        assert ph.vendor_id == a.vendor_id             # cost row re-pointed
        assert vendor_matching_summary(s)['possible_duplicates'] == 0


def test_summary_shape():
    with _session() as s:
        resolve_vendor(s, source='qb', external_id='v1', name='A')
        summ = vendor_matching_summary(s)
        assert set(summ) >= {'total', 'by_status', 'needs_review', 'possible_duplicates', 'vendors'}
