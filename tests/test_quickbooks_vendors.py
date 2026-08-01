"""QuickBooks vendor translator (Tier 2): !VEND -> Vendor, with vault + dedup."""
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

import app.models  # noqa: F401
from app.connectors.base import run_translation
from app.connectors.quickbooks.vendors import VendorListTranslator
from app.models.connector_tables import ExternalIdentityMap
from app.models.translator_tables import RawSourceCell, RawSourceRow, SourceArtifact
from app.models.vendor_tables import Vendor, VendorProfile

_VCOLS = 45
_HEADER = '!VEND\t' + '\t'.join([
    'NAME', 'REFNUM', 'TIMESTAMP', 'PRINTAS', 'ADDR1', 'ADDR2', 'ADDR3', 'ADDR4', 'ADDR5', 'VTYPE',
    'CONT1', 'CONT2', 'PHONE1', 'PHONE2', 'FAXNUM', 'EMAIL', 'NOTE', 'TAXID', 'LIMIT', 'TERMS', 'NOTEPAD',
    'SALUTATION', 'COMPANYNAME', 'FIRSTNAME', 'MIDINIT', 'LASTNAME',
    *[f'CUSTFLD{i}' for i in range(1, 16)], '1099', 'HIDDEN', 'DELCOUNT',
])


def _vend(name, refnum, **kw):
    c = [''] * _VCOLS
    c[0], c[1], c[2] = 'VEND', name, refnum
    c[4] = kw.get('printas', '')
    c[13] = kw.get('phone', '')
    c[16] = kw.get('email', '')
    c[18] = kw.get('taxid', '')
    c[23] = kw.get('company', '')
    c[24] = kw.get('firstname', '')
    c[26] = kw.get('lastname', '')
    c[42] = kw.get('is1099', '')
    c[43] = kw.get('hidden', '')
    return '\t'.join(c)


def _iif() -> bytes:
    lines = [
        '!HDR\tPROD\tVER', 'HDR\tQuickBooks\t2021',
        '!ACCNT\tNAME\tREFNUM\tTIMESTAMP\tACCNTTYPE', 'ACCNT\tGeneral Checking\t1\t0\tBANK',
        _HEADER,
        _vend('Poolcorp', '10'),
        _vend('PC-Repairs', '11', company='Pool Corp LLC'),
        _vend('John Smith Handyman', '12', firstname='John', lastname='Smith'),
        _vend('Old Vendor', '13', hidden='Y'),
        _vend('Contractor Bob', '14', is1099='Y', taxid='55-1234567'),
        _vend('OUTGOING WIRE', '15'),
        _vend('Premier Painting', '16'),
        _vend('Premier Paitning', '17'),
        '',
    ]
    return ('\r\n'.join(lines)).encode('cp1252')


def _run():
    engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
    SQLModel.metadata.create_all(engine)
    s = Session(engine)
    art = SourceArtifact(source_slug='quickbooks', artifact_type='report_vendor_list')
    s.add(art); s.commit(); s.refresh(art)
    raw = _iif()
    summary = run_translation(s, art, raw, VendorListTranslator())
    return s, art, raw, summary


def test_byte_roundtrip_crlf():
    s, art, raw, _ = _run()
    for r in s.exec(select(RawSourceRow).where(RawSourceRow.artifact_id == art.id)).all():
        assert raw[r.byte_offset_start:r.byte_offset_end].decode('cp1252') == r.raw_line_text


def test_vend_rows_become_vendors():
    s, art, raw, _ = _run()
    names = {v.name for v in s.exec(select(Vendor)).all()}
    assert {'Poolcorp', 'PC-Repairs', 'John Smith Handyman', 'Old Vendor', 'Contractor Bob'} <= names
    assert 'OUTGOING WIRE' not in names


def test_companyname_override_keeps_raw_name_key():
    s, art, raw, _ = _run()
    v = s.exec(select(Vendor).where(Vendor.name == 'PC-Repairs')).first()
    p = s.exec(select(VendorProfile).where(VendorProfile.vendor_id == v.id)).first()
    assert v.name == 'PC-Repairs'                 # immutable key
    assert p.display_name == 'Pool Corp LLC'      # display from COMPANYNAME


def test_person_vendor_uses_person_name():
    s, art, raw, _ = _run()
    v = s.exec(select(Vendor).where(Vendor.name == 'John Smith Handyman')).first()
    p = s.exec(select(VendorProfile).where(VendorProfile.vendor_id == v.id)).first()
    assert p.person_name == 'John Smith'


def test_hidden_vendor_created_inactive():
    s, art, raw, _ = _run()
    v = s.exec(select(Vendor).where(Vendor.name == 'Old Vendor')).first()
    assert v.is_active is False
    row = s.exec(select(RawSourceRow).where(RawSourceRow.raw_line_text.contains('Old Vendor'))).first()
    assert row.status == 'interpreted'            # retained, not dropped


def test_taxid_cell_encrypted_not_plaintext():
    s, art, raw, _ = _run()
    v = s.exec(select(Vendor).where(Vendor.name == 'Contractor Bob')).first()
    p = s.exec(select(VendorProfile).where(VendorProfile.vendor_id == v.id)).first()
    assert p.is_1099 is True
    assert p.tax_id_hash != '' and p.tax_id_last4 == '4567'
    # the raw cell was blanked; the encrypted value is in the vault, hash present
    tax_cell = s.exec(select(RawSourceCell).where(RawSourceCell.header_name == 'TAXID',
                                                  RawSourceCell.is_sensitive == True)).all()  # noqa: E712
    bob_cells = [c for c in tax_cell if c.cipher_value]
    assert bob_cells and all(c.raw_value == '' for c in bob_cells)
    assert all(c.value_hash for c in bob_cells)


def test_denylist_excluded_with_reason():
    s, art, raw, _ = _run()
    row = s.exec(select(RawSourceRow).where(RawSourceRow.raw_line_text.contains('OUTGOING WIRE'))).first()
    assert row.status == 'excluded' and row.quarantine_reason == 'not_a_trade_vendor'


def test_near_duplicate_flagged_not_merged():
    s, art, raw, _ = _run()
    prem = [v for v in s.exec(select(Vendor)).all() if v.name.startswith('Premier Pai')]
    assert len(prem) == 2                          # both kept
    flagged = [m for m in s.exec(select(__import__('app.models.vendor_tables', fromlist=['VendorMatch']).VendorMatch)).all()
               if m.status == 'flagged']
    assert flagged


def test_accnt_and_headers_retained_excluded():
    s, art, raw, _ = _run()
    accnt = s.exec(select(RawSourceRow).where(RawSourceRow.band == 'ACCNT',
                                              RawSourceRow.record_type == 'data')).first()
    assert accnt.status == 'excluded' and accnt.quarantine_reason == 'handled_by_tier0_coa'
    headers = s.exec(select(RawSourceRow).where(RawSourceRow.record_type == 'header')).all()
    assert headers and all(h.status == 'excluded' for h in headers)


def test_every_row_terminal():
    s, art, raw, _ = _run()
    rows = s.exec(select(RawSourceRow).where(RawSourceRow.artifact_id == art.id)).all()
    assert all(r.status in {'interpreted', 'excluded', 'superseded', 'quarantined_parse'} for r in rows)


def test_reingest_is_idempotent_no_duplicate_vendors_or_idmaps():
    s, art, raw, _ = _run()
    v1 = len(s.exec(select(Vendor)).all())
    m1 = len(s.exec(select(ExternalIdentityMap).where(ExternalIdentityMap.entity_type == 'vendor')).all())
    # Second ingest of the same bytes as a new artifact.
    art2 = SourceArtifact(source_slug='quickbooks', artifact_type='report_vendor_list')
    s.add(art2); s.commit(); s.refresh(art2)
    run_translation(s, art2, raw, VendorListTranslator())
    assert len(s.exec(select(Vendor)).all()) == v1                     # no duplicate vendors
    assert len(s.exec(select(ExternalIdentityMap).where(
        ExternalIdentityMap.entity_type == 'vendor')).all()) == m1     # no duplicate id-maps
