"""Vendor list translator (Tier 2): IIF !VEND rows -> Vendor (via resolve_vendor).

Mirrors ChartOfAccountsTranslator. Every !VEND data row becomes a resolved Vendor
(dedup/flag/never-orphan); placeholder "vendors" that are really bank artifacts
(OUTGOING WIRE, etc.) are excluded with a reason via an owner-confirmable denylist;
every other band/row is retained and reason-coded. TAXID cells are marked
sensitive so the framework vaults them encrypted (dormant on this file: 0 TAXIDs).
"""
from __future__ import annotations

from sqlmodel import Session, select

from app.connectors.base import BaseTranslator, ClassifyResult, InterpretResult
from app.connectors.quickbooks.coa import _unquote
from app.connectors.quickbooks.iif import tokenize_iif
from app.core.secrets import decrypt, norm_sensitive
from app.models.connector_tables import ExternalIdentityMap
from app.models.translator_tables import SourceArtifact
from app.services.vendor_matching import resolve_vendor

# Exact-NAME denylist (case-insensitive): rows QuickBooks keeps in the vendor list
# that are really bank/ledger artifacts, not trade vendors. Denylist ONLY (never a
# heuristic) so legit short/all-caps vendors (USPS, FKAA, CVS, KFC, AFCO) survive.
NON_VENDOR_NAMES = {
    'outgoing wire', 'wire transfer fee', 'unknown check', 'charge back', 'debit', 'eval', 'rent deposit',
}


class VendorListTranslator(BaseTranslator):
    source_slug = 'quickbooks'
    artifact_types = ('report_vendor_list',)

    def tokenize(self, raw_bytes: bytes, artifact: SourceArtifact) -> list:
        rows, encoding = tokenize_iif(raw_bytes)
        artifact.encoding_detected = encoding
        # Mark TAXID cells sensitive so the driver vaults them (encrypt + keyed hash).
        for row in rows:
            for c in row.cells:
                if c.header_name == 'TAXID':
                    c.is_sensitive = True
        return rows

    def classify(self, row, cells) -> ClassifyResult:
        if row.band == 'VEND' and row.record_type == 'data':
            return ClassifyResult(record_type='data', band='VEND')
        if row.record_type == 'header':
            return ClassifyResult(skip_interpret=True, reason='iif_header')
        if row.record_type == 'blank':
            return ClassifyResult(skip_interpret=True, reason='blank')
        if row.band == 'ACCNT':
            return ClassifyResult(skip_interpret=True, reason='handled_by_tier0_coa')
        if row.band == 'HDR':
            return ClassifyResult(skip_interpret=True, reason='iif_file_meta')
        if row.band in ('CUSTNAMEDICT', 'CUSTITEMDICT', 'ENDCUSTNAMEDICT', 'ENDCUSTITEMDICT'):
            return ClassifyResult(skip_interpret=True, reason='iif_list_dictionary')
        return ClassifyResult(skip_interpret=True, reason=f'not_a_vendor_list:{row.band or "unknown"}')

    def interpret(self, session: Session, row, cells) -> InterpretResult:
        d = {c.header_name: _unquote(c.raw_value) for c in cells if c.header_name}
        raw_name = d.get('NAME', '').strip()
        if not raw_name:
            raise ValueError('VEND row missing NAME')
        if raw_name.lower() in NON_VENDOR_NAMES:
            return InterpretResult(status='excluded', reason='not_a_trade_vendor')

        company = d.get('COMPANYNAME', '').strip()
        printas = d.get('PRINTAS', '').strip()
        person = ' '.join(x for x in (d.get('SALUTATION', ''), d.get('FIRSTNAME', ''),
                                      d.get('MIDINIT', ''), d.get('LASTNAME', '')) if x).strip()
        display_name = company or printas or person or raw_name
        address_block = '\n'.join(x for x in (d.get('ADDR1', ''), d.get('ADDR2', ''), d.get('ADDR3', ''),
                                              d.get('ADDR4', ''), d.get('ADDR5', '')) if x).strip()
        is_active = d.get('HIDDEN', '').strip().upper() != 'Y'
        is_1099 = d.get('1099', '').strip().upper() == 'Y'

        # TAXID: plaintext was vaulted (encrypted) at persist time; read hash + last4
        # from the sensitive cell (raw_value is blanked). 0 TAXIDs on the real file.
        tax_cell = next((c for c in cells if c.header_name == 'TAXID' and c.is_sensitive), None)
        tax_id_hash, tax_id_last4 = '', ''
        if tax_cell and tax_cell.cipher_value:
            tax_id_hash = tax_cell.value_hash
            try:
                tax_id_last4 = norm_sensitive(decrypt(tax_cell.cipher_value))[-4:]
            except Exception:
                tax_id_last4 = ''

        external_id = d.get('REFNUM', '').strip() or raw_name
        result = resolve_vendor(
            session, source='quickbooks', external_id=external_id, name=raw_name, company=company,
            person=person, display_name=display_name, billing_name=printas, address_block=address_block,
            notes=(d.get('NOTE', '') or d.get('NOTEPAD', '')).strip(), terms=d.get('TERMS', '').strip(),
            vendor_type=(d.get('VTYPE', '').strip() or 'supplier'),
            email=d.get('EMAIL', '').strip(), phone=d.get('PHONE1', '').strip(),
            tax_id_hash=tax_id_hash, tax_id_last4=tax_id_last4, is_active=is_active, is_1099=is_1099,
            artifact_id=row.artifact_id, row_id=row.id,
        )
        if result.vendor_id:
            # Idempotent: re-ingesting the same vendor list must not pile up duplicate
            # id-map rows (ExternalIdentityMap has no unique constraint). Guard the
            # insert like skimmer_sync / front_desk do.
            exists = session.exec(
                select(ExternalIdentityMap).where(
                    ExternalIdentityMap.source_slug == 'quickbooks',
                    ExternalIdentityMap.entity_type == 'vendor',
                    ExternalIdentityMap.external_id == external_id,
                )
            ).first()
            if not exists:
                session.add(ExternalIdentityMap(
                    source_slug='quickbooks', entity_type='vendor', external_id=external_id,
                    internal_type='vendor', internal_id=str(result.vendor_id), confidence=result.confidence,
                ))
                session.commit()
        return InterpretResult(status='interpreted')
