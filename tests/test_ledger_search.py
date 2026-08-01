"""Cross-vendor ledger search: find an item / part # / invoice # across vendors."""
from datetime import date

from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

import app.models  # noqa: F401
from app.services.invoice_import import ingest_parsed_invoices, parse_ace_text, parse_heritage_paste
from app.services.ledger_search import search_ledger


def _session() -> Session:
    engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
    SQLModel.metadata.create_all(engine)
    return Session(engine)


_HERITAGE = '\n'.join([
    'Invoice # 0026667528-001', 'PO #: KRIS', 'Placed by KEY WEST POOL SERVICE AND',
    'Invoice Date: 05/08/26 Due Date: 06/07/26', 'Invoice Status: Paid', 'Branch Details:',
    'HERITAGE POOL SUPPLY OPA LOCKA', 'Product Description', 'Qty', 'UOM', 'Unit Price', 'Ext. Price',
    'Reorder Qty', 'Jandy FloPro Single-Speed Residential 1 hp In-Ground Pool Pump',
    'ITEM # JNDFHPM10 MFG # FHPM1.0', '3', 'EA', '$632.74 /EA', '$1,898.22', 'Qty',
    'Invoice Summary', 'Subtotal', '$1,898.22', 'Shipping & Charges', '$0.00', 'Tax Total', '$142.36',
    'Total', '$2,040.58',
])
_ACE = '\n'.join([
    '** AMOUNT CHARGED TO STORE ACCOUNT ** 22.56', '981825', '6/22/26',
    'QUANTITY UM ITEM DESCRIPTION SUGG PRICE /PER EXTENSION',
    '2 EA 7225246 DC POOL SALT 40LB 13.99 10.493 /EA 20.99 C',
])


def _load(s):
    ingest_parsed_invoices(s, parse_heritage_paste(_HERITAGE))
    ingest_parsed_invoices(s, [parse_ace_text(_ACE, '981825', date(2026, 6, 22))])


def test_search_by_product_name():
    with _session() as s:
        _load(s)
        res = search_ledger(s, 'flopro')
        assert len(res['products']) == 1
        hit = res['products'][0]
        assert hit.mfg_no == 'FHPM1.0'
        assert hit.points and hit.points[0].vendor == 'Heritage Pool Supply'
        assert round(hit.points[0].unit_cost, 2) == 632.74


def test_search_by_part_number():
    with _session() as s:
        _load(s)
        assert search_ledger(s, 'FHPM1.0')['products'][0].name.startswith('Jandy FloPro')


def test_search_by_invoice_number_partial():
    with _session() as s:
        _load(s)
        res = search_ledger(s, '0026667528')
        assert len(res['invoices']) == 1
        inv = res['invoices'][0]
        assert inv.vendor == 'Heritage Pool Supply' and inv.line_count == 1


def test_search_ace_item():
    with _session() as s:
        _load(s)
        res = search_ledger(s, 'pool salt')
        assert res['products'][0].points[0].vendor == 'Strunks Ace Hardware'
        assert res['products'][0].sku == '7225246'


def test_empty_query_returns_nothing():
    with _session() as s:
        _load(s)
        assert search_ledger(s, '') == {'products': [], 'invoices': []}
