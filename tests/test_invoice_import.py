"""Heritage portal-paste invoice import -> product + per-vendor price ledger.
Fixtures are real invoices from the owner's Heritage Invoice History."""
from datetime import date

from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

import app.models  # noqa: F401
from app.models.tables import ChemicalProduct, InvoiceDocument, ProductPriceHistory
from datetime import date as _date
from app.models.vendor_tables import Vendor
from app.services.invoice_import import ingest_parsed_invoices, parse_ace_text, parse_heritage_paste
from app.services.purchasing import best_source_for_product


def _session() -> Session:
    engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
    SQLModel.metadata.create_all(engine)
    return Session(engine)


def _inv(no, dt, po, status, lines, subtotal, shipping, tax, total, job=''):
    p = [f'Invoice # {no}', f'PO #: {po}']
    if job:
        p.append(f'Job Name: {job}')
    p += ['Placed by KEY WEST POOL SERVICE AND', f'Invoice Date: {dt} Due Date: 06/07/26',
          f'Invoice Status: {status}', 'Documents:', 'Bill to:',
          'KEY WEST POOL SERVICE AND DE 800 14TH ST KEY WEST, FL 33040', 'Branch Details:',
          'HERITAGE POOL SUPPLY OPA LOCKA 2358 NW 151 ST OPA LOCKA, FL 33054 (305)-622-7312',
          'Product Description', 'Qty', 'UOM', 'Unit Price', 'Ext. Price', 'Reorder Qty']
    for (desc, item, mfg, qty, uom, unit, ext) in lines:
        p += [desc, f'ITEM # {item} MFG # {mfg}', str(qty), uom, f'{unit} /{uom}', ext, 'Qty']
    p += ['Invoice Summary', 'Subtotal', subtotal, 'Shipping & Charges', shipping,
          'Tax Total', tax, 'Total', total]
    return '\n'.join(p)


# Real invoices from the paste.
_PASTE = '\n'.join([
    _inv('0026667528-001', '05/08/26', 'KRIS', 'Paid',
         [('Jandy FloPro Single-Speed Residential 1 hp 115/230V Single-Phase In-Ground Pool Pump',
           'JNDFHPM10', 'FHPM1.0', 3, 'EA', '$632.74', '$1,898.22')],
         '$1,898.22', '$0.00', '$142.36', '$2,040.58'),
    _inv('0027187238-001', '05/28/26', '720stock', 'Paid',
         [('Jandy FloPro Single-Speed Residential 1 hp 115/230V Single-Phase In-Ground Pool Pump',
           'JNDFHPM10', 'FHPM1.0', 2, 'EA', '$632.74', '$1,265.48')],
         '$1,265.48', '$0.00', '$94.91', '$1,360.39'),
    _inv('0027913967-002', '06/30/26', 'STOCK', 'Paid',
         [('Reducing Bushing, 2 x 1-1/2" Spigot x Slip White PVC Schedule 40', 'S4PBH251', '437-251BC', 10, 'EA', '$1.56', '$15.60'),
          ('Coupling, 2" Slip White PVC Schedule 40', 'S4PCP020', '429-020BC', 20, 'EA', '$0.96', '$19.20')],
         '$34.80', '$0.00', '$2.61', '$37.41'),
    _inv('0027571674-001CM', '06/19/26', 'DEFFECT 022056', 'Paid',
         [('Pentair IntelliFloXF VSF Variable 3.95 hp 230V Pool Pump', 'PEN022056', '022056', -1, 'EA', '$1,900.87', '-$1,900.87')],
         '-$1,900.87', '$0.00', '-$142.56', '-$2,043.43'),
])


def test_parse_extracts_fields_and_mfg_key():
    invs = parse_heritage_paste(_PASTE)
    assert len(invs) == 4
    first = invs[0]
    assert first.invoice_no == '0026667528-001'
    assert first.vendor_name == 'Heritage Pool Supply'
    assert first.invoice_date == date(2026, 5, 8)
    assert first.po == 'KRIS'
    line = first.lines[0]
    assert line.mfg_no == 'FHPM1.0' and line.item_no == 'JNDFHPM10'
    assert line.qty == 3 and line.uom == 'EA' and line.unit_price == 632.74 and line.ext_price == 1898.22
    assert line.arithmetic_ok is True
    assert first.totals_ok is True


def test_multi_line_and_credit_memo_flagged():
    invs = {i.invoice_no: i for i in parse_heritage_paste(_PASTE)}
    assert len(invs['0027913967-002'].lines) == 2          # multi-line
    cm = invs['0027571674-001CM']
    assert cm.is_credit is True                            # ...CM + negative total
    assert cm.lines[0].qty == -1 and cm.lines[0].ext_price == -1900.87


def test_ingest_prices_products_by_mfg_excluding_credits():
    with _session() as s:
        summary = ingest_parsed_invoices(s, parse_heritage_paste(_PASTE))
        assert summary['invoices_imported'] == 4
        assert summary['credit_memos'] == 1
        assert summary['lines_excluded_credit'] == 1        # the Pentair return
        assert summary['lines_priced'] == 4                 # 2 Jandy + 2 PVC

        # FHPM1.0 is ONE product with TWO dated price points (the pump on two invoices)
        pump = s.exec(select(ChemicalProduct).where(ChemicalProduct.manufacturer_part_number == 'FHPM1.0')).first()
        assert pump is not None
        prices = s.exec(select(ProductPriceHistory).where(ProductPriceHistory.product_id == pump.id)).all()
        assert len(prices) == 2 and all(round(p.unit_cost, 2) == 632.74 for p in prices)

        # the credit-memo Pentair product exists but has NO price point
        pen = s.exec(select(ChemicalProduct).where(ChemicalProduct.manufacturer_part_number == '022056')).first()
        assert pen is not None
        assert s.exec(select(ProductPriceHistory).where(ProductPriceHistory.product_id == pen.id)).all() == []

        # best-source reads it
        bs = best_source_for_product(s, pump)
        assert bs is not None and bs.best_vendor == 'Heritage Pool Supply' and round(bs.best_unit_cost, 2) == 632.74


def test_reingest_is_idempotent():
    with _session() as s:
        ingest_parsed_invoices(s, parse_heritage_paste(_PASTE))
        p1 = len(s.exec(select(ProductPriceHistory)).all())
        summary = ingest_parsed_invoices(s, parse_heritage_paste(_PASTE))
        assert summary['invoices_skipped_dup'] == 4
        assert len(s.exec(select(ProductPriceHistory)).all()) == p1     # no new price rows


# --- trickier real shapes from the paste ---

def test_mfg_zero_falls_back_to_item_key():
    paste = _inv('0028396082-001', '07/21/26', 'paradise', 'Unpaid',
                 [('Florida Spa Rules Sign 24" x 36"', 'NASFL4', '0', 1, 'EA', '$19.55', '$19.55')],
                 '$19.55', '$0.00', '$1.46', '$21.01', job='paradise')
    inv = parse_heritage_paste(paste)[0]
    assert inv.lines[0].mfg_no == ''                      # MFG # 0 treated as absent
    assert inv.job == 'paradise'
    with _session() as s:
        ingest_parsed_invoices(s, [inv])
        prod = s.exec(select(ChemicalProduct).where(ChemicalProduct.sku == 'NASFL4')).first()
        assert prod is not None and prod.manufacturer_part_number == ''   # keyed on item #


def test_ft_unit_and_service_prefix():
    paste = _inv('0027913967-001', '06/25/26', 'STOCK', 'Paid',
                 [('2" x 20\' Schedule 40, Bell End PVC Pipe', 'BEP020SCH40', '022620', 30, 'FT', '$0.85', '$25.50')],
                 '$25.50', '$0.00', '$1.91', '$27.41')
    line = parse_heritage_paste(paste)[0].lines[0]
    assert line.uom == 'FT' and line.unit_price == 0.85 and line.qty == 30

    # a description that carries a "Heritage Pro Service" prefix line still keys on MFG #
    paste2 = _inv('0027152434-001', '05/28/26', 'Havana', 'Paid',
                  [('Heritage Pro Service\nUS Motors Aqua-Shield Pump Motor 1.65 hp Single-Phase 48Y Square Flange',
                    'NIDASQ165', 'ASQ165', 1, 'EA', '$235.95', '$235.95')],
                  '$235.95', '$0.00', '$17.70', '$253.65')
    l2 = parse_heritage_paste(paste2)[0].lines[0]
    assert l2.mfg_no == 'ASQ165' and 'US Motors' in l2.description


# --- Strunks Ace Hardware PDFs (real extracted text: jumbled header + clean lines) ---

_ACE_TEXT = '\n'.join([
    'KEYS POOL SERVICE & DESIGN', '2711 SEIDENBERG AVE', 'NET 10TH',
    '37.16', '0.00', '37.16', '6:02', '2.79', '6/17/26',
    '305-731-4448 PO # SOUTHERNMOST INN', 'INVOICE:',
    '** AMOUNT CHARGED TO STORE ACCOUNT ** 39.95', '981386', '39.95',
    'QUANTITY UM ITEM DESCRIPTION SUGG PRICE /PER EXTENSION',
    '1 EA 2199750 BIT DRILL 7/16" 1/4SHANK 10.69 /EA 10.69',
    '1 EA 2251429 ADJUSTABLE WRENCH 6" 9.69 /EA 9.69',
    '1 EA 4037389 PIPE THREAD SEAL 1/2X260 1.99 /EA 1.99',
    '1 EA 23136 TAP CARDED 1/4X18NPT 14.79 /EA 14.79',
])

# Pool-salt line carries a SUGG retail (13.99) before the cost (10.493).
_ACE_SALT = '\n'.join([
    '** AMOUNT CHARGED TO STORE ACCOUNT ** 22.56', '981825', '6/22/26',
    'QUANTITY UM ITEM DESCRIPTION SUGG PRICE /PER EXTENSION',
    '2 EA 7225246 DC POOL SALT 40LB 13.99 10.493 /EA 20.99 C',
])


def test_ace_parses_lines_total_and_reconciles():
    inv = parse_ace_text(_ACE_TEXT, '981386', _date(2026, 6, 17), po='SOUTHERNMOST INN')
    assert inv.vendor_name == 'Strunks Ace Hardware'
    assert inv.total == 39.95 and inv.subtotal == 37.16 and inv.tax == 2.79
    assert inv.totals_ok is True and len(inv.lines) == 4
    l0 = inv.lines[0]
    assert l0.item_no == '2199750' and l0.mfg_no == '' and l0.qty == 1
    assert l0.unit_price == 10.69 and l0.ext_price == 10.69 and l0.arithmetic_ok


def test_ace_drops_sugg_price_keeps_cost():
    inv = parse_ace_text(_ACE_SALT, '981825', _date(2026, 6, 22))
    l = inv.lines[0]
    assert l.item_no == '7225246'
    assert l.description == 'DC POOL SALT 40LB'      # sugg 13.99 dropped from the name
    assert l.unit_price == 10.493 and l.ext_price == 20.99   # cost, not the 13.99 retail
    assert inv.total == 22.56


def test_ace_ingests_keyed_on_item_number():
    with _session() as s:
        ingest_parsed_invoices(s, [parse_ace_text(_ACE_TEXT, '981386', _date(2026, 6, 17))])
        drill = s.exec(select(ChemicalProduct).where(ChemicalProduct.sku == '2199750')).first()
        assert drill is not None and drill.manufacturer_part_number == ''   # no MFG # -> item-keyed
        assert s.exec(select(ProductPriceHistory).where(ProductPriceHistory.product_id == drill.id)).all()


def test_mixed_vendor_ingest_resolves_each_vendor():
    with _session() as s:
        invoices = parse_heritage_paste(_PASTE) + [parse_ace_text(_ACE_TEXT, '981386', _date(2026, 6, 17))]
        ingest_parsed_invoices(s, invoices)
        names = {v.name for v in s.exec(select(Vendor)).all()}
        assert 'Heritage Pool Supply' in names and 'Strunks Ace Hardware' in names


def test_item_with_no_mfg_field_parses():
    # e.g. a -$35 shipping credit line "ITEM # 900" with no "MFG #"
    block = '\n'.join([
        'Invoice # 0028168641-001CM', 'Placed by KEY WEST POOL SERVICE AND',
        'Invoice Date: 07/07/26 Due Date: 08/06/26', 'Invoice Status: Paid', 'Branch Details:',
        'HERITAGE POOL SUPPLY OPA LOCKA', 'Product Description', 'Qty', 'UOM', 'Unit Price',
        'Ext. Price', 'Reorder Qty', 'ITEM # 900', '-1', 'EA', '$0.00 /EA', '$0.00', 'Qty',
        'Invoice Summary', 'Subtotal', '$0.00', 'Shipping & Charges', '-$35.00',
        'Tax Total', '$0.00', 'Total', '-$35.00',
    ])
    inv = parse_heritage_paste(block)[0]
    assert inv.is_credit is True                          # ...CM and negative total
    assert inv.lines[0].item_no == '900' and inv.lines[0].mfg_no == ''
