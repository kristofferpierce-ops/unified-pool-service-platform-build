I have verified every load-bearing fact against the real repo. All prior findings check out at the cited lines. Here is the build-ready spec.

---

# QuickBooks Tier 2 â€” VENDOR IDENTITY SPINE
## Build-ready implementation spec (design only)

Repo root: `C:/Users/krist/Desktop/unified_pool_service_platform_build/unified_pool_service_platform_build/`
Mirrors the shipped customer spine (`app/services/customer_matching.py`, `app/models/customer_tables.py`) and the shipped Tier-0 translator (`app/connectors/quickbooks/coa.py`). Fully additive: **no edits to `customer_matching.py`, `customer_tables.py`, or any live customer code.** One shared-framework change is required (`app/connectors/base.py:152`, Â§4) and is a genuine no-loss fix, not gold-plating.

Verified ground truth this spec is built on:
- `resolve_customer` + helpers exactly as documented (`customer_matching.py:130-227`, thresholds `:32-33`, `MatchResult :57-64`, `merge_account :267-296`, `matching_summary :299-312`).
- `ExternalIdentityMap` discriminators are free-text (`connector_tables.py:91-100`) â€” `entity_type='vendor'`/`internal_type='vendor'` need **no schema change**.
- `RawSourceCell` vault fields exist (`translator_tables.py:86-103`) but are **dead**: `base.py:152` blanks sensitive `raw_value` and never writes `cipher_value`/`value_hash`. TAXID would be silently dropped today â€” no-loss is currently violated for sensitive cells.
- No crypto library in the venv (`requirements.txt` has none); `config.py:1-25` sources **no secret**.
- `coa.py:129-130` defers `!VEND` rows with reason `deferred_to_tier2_vendors` â€” this spec is the consumer of that deferral.
- Real source `data/imports/quickbooks/qb_lists.IIF`: 357 `!VEND` rows, `!VEND` header at line 136, **0 TAXID / 0 EMAIL / 0 1099=Y / 0 HIDDEN=Y**, NAME 100% populated, ADDR1 is a NAME echo, **no `!INVITEM` band (0 items)**.

---

## 1. MODELS

New module `app/models/vendor_tables.py` (mirrors `customer_tables.py`). Register in `app/models/__init__.py` so `SQLModel.metadata.create_all` picks it up (same import posture the customer tables use). SQLite adds these as fresh tables cleanly â€” same migration posture as `asset_tables.py:9-11`.

### 1.1 `Vendor` â€” analog of `Account` (`tables.py:80-85`)

| Field | Type | Notes |
|---|---|---|
| `id` | `Optional[int]` PK | |
| `vendor_type` | `str = Field(default='supplier', index=True)` | from IIF `VTYPE`; `supplier` default (VTYPE is 0-filled in real data) |
| `name` | `str = Field(index=True)` | **immutable natural key = raw IIF `NAME`. Never overwritten** (transactions reference NAME; data analysis Â§2) |
| `billing_name` | `str = ''` | `PRINTAS` ("print on check as") |
| `notes` | `str = ''` | `NOTE`/`NOTEPAD` verbatim |
| `address_block` | `str = ''` | `ADDR1..5` kept as one multi-line block (design Â§2.2). ADDR1 echoes NAME for 348/357 â€” preserved verbatim, never used as a match signal |
| `is_active` | `bool = True` | `HIDDEN=Y` â†’ `False`; excluded from auto-match |

### 1.2 `VendorProfile` â€” analog of `CustomerProfile` (`customer_tables.py:20-33`), the match-key carrier

| Field | Type | Notes |
|---|---|---|
| `id` | `Optional[int]` PK | |
| `vendor_id` | `int = Field(index=True, unique=True)` | 1:1 with `Vendor` (mirrors `CustomerProfile.account_id` `:24`) |
| `display_name` | `str = Field(default='', index=True)` | canonical display (resolution in Â§3.4) |
| `company_name` | `str = ''` | `COMPANYNAME` |
| `person_name` | `str = ''` | `SALUTATION FIRSTNAME MIDINIT LASTNAME`; **the resolution key when `COMPANYNAME` blank** (design Â§2.2) |
| `email` | `str = Field(default='', index=True)` | `EMAIL` (norm: lowercase/strip) |
| `phone` | `str = Field(default='', index=True)` | `PHONE1` (norm: last-10-digits, like `norm_phone` `:40-43`) |
| `tax_id_hash` | `str = Field(default='', index=True)` | **keyed HMAC** of normalized TAXID â€” the Pass-1 match key. Never plaintext (Â§4) |
| `tax_id_last4` | `str = ''` | masked display only; render `**-***{last4}` |
| `terms` | `str = ''` | `TERMS` |
| `is_1099` | `bool = Field(default=False, index=True)` | the `1099` flag; `True` routes to the contractor-review filter |
| `is_active` | `bool = Field(default=True, index=True)` | copied from `Vendor.is_active`; the resolver skips inactive profiles as candidates |
| `primary_source` | `str = ''` | `quickbooks | manual` |
| `source_artifact_id` | `Optional[int] = Field(default=None, index=True)` | provenance â†’ the `RawSourceCell` vault holding the encrypted TAXID (mirrors `ExpenseActual.artifact_id`/`source_row_id` `:163-164`) |
| `source_row_id` | `Optional[int] = Field(default=None, index=True)` | |
| `created_at`, `updated_at` | `datetime` | |

**No plaintext or ciphertext TAXID is stored on `VendorProfile`.** The single encrypted copy lives in `RawSourceCell.cipher_value` (Â§4); `VendorProfile` carries only the keyed hash (match) + last-4 (display) + a provenance pointer for the gated decrypt. One decrypt surface, not two.

### 1.3 `VendorMatch` â€” analog of `CustomerMatch` (`customer_tables.py:36-61`)

| Field | Type | Notes |
|---|---|---|
| `id` | `Optional[int]` PK | |
| `source_slug` | `str = Field(index=True)` | `quickbooks | manual | ...` |
| `external_id` | `str = Field(default='', index=True)` | IIF `REFNUM` (357 unique in real data), fallback `NAME` |
| `external_name` | `str = ''` | |
| `external_email` | `str = Field(default='', index=True)` | |
| `external_phone` | `str = ''` | |
| `external_company` | `str = ''` | |
| `external_tax_id_hash` | `str = Field(default='', index=True)` | denormalized keyed hash for the review queue |
| `vendor_id` | `Optional[int] = Field(default=None, index=True)` | resolved vendor, `None` if unmatched |
| `match_pass` | `int = Field(default=0, index=True)` | 0 unmatched / 1 tax-id-or-new / 2 assisted / 3 manual |
| `status` | `str = Field(default='unmatched', index=True)` | `auto \| flagged \| suggested \| unmatched` (+ `confirmed`). **Emit the code's status set, not a "manual" docstring** â€” the customer model comment `customer_tables.py:54` says "manual" but the code emits `flagged` (`:207`); mirror the code |
| `confidence` | `float = 0.0` | |
| `candidates_json` | `str = '[]'` | `[{vendor_id, name, score, reason}]` |
| `notes` | `str = ''` | |
| `created_at`, `updated_at` | `datetime` | |

### 1.4 External identity â€” reuse `ExternalIdentityMap` (`connector_tables.py:91-100`)

`entity_type='vendor'`, `internal_type='vendor'`, `internal_id=str(vendor_id)`, `external_id=REFNUM`. Zero changes to `connector_tables.py`. This is the same idempotency/dedup mechanism already used by `skimmer_sync.py` / `front_desk.py`, so QB re-exports re-link deterministically.

### 1.5 Cost-linkage FK decision (additive nullable FK + keep the string)

Per design Â§4.4 item 6 ("Add FKs from `ProductPriceHistory`, `AssetRecord`, `CommercialVendorOrder`, `ExpenseItem`"), add a nullable `vendor_id` **beside** â€” never replacing â€” each existing free-text `vendor_name`:

- `ProductPriceHistory` (`tables.py:31-41`, string at `:34`) â†’ add `vendor_id: Optional[int] = Field(default=None, index=True)`
- `ChemicalProduct` (`tables.py:17-28`, `default_vendor` string at `:25`) â†’ add `default_vendor_id: Optional[int] = Field(default=None, index=True)`
- `AssetRecord` (`asset_tables.py:40`) â†’ add `vendor_id: Optional[int] = ...`
- `CommercialVendorOrder` (`tables.py:211`) â†’ add `vendor_id: Optional[int] = ...`

Rationale (rejecting the two alternatives):
- **Hard FK (drop the string)** breaks `purchasing.py` immediately â€” its entire supplier price-book treats "a supplier" as `row.vendor_name or '(unknown)'` (`purchasing.py:10-12,81,144`) and would need a non-null backfill of 357 vendors before anything works.
- **String-only + map** leaves cost rows unable to cheaply join vendor attributes (terms, 1099, tax_id).
- **Nullable-FK-beside-string** is purely additive (SQLite adds nullable columns cleanly), keeps the verbatim string as the no-loss/display fallback, lets resolution be gradual and gated, and exactly matches the shipped `Account`/`CustomerProfile`/`ExternalIdentityMap` pattern. Nothing reading `vendor_name` today breaks; `purchasing.py` keeps grouping on the string and can later prefer `vendor_id` (group by `vendor_id` falling back to `vendor_name`).

**In Tier-2 scope:** create the tables + add the nullable columns (additive, safe). **Out of Tier-2 scope:** backfilling `vendor_id` onto existing cost rows and rewriting `purchasing.py`'s grouping â€” a separate later change on live tables (Â§6).

---

## 2. `resolve_vendor` ALGORITHM

New module `app/services/vendor_matching.py`. Mirrors `resolve_customer` (`customer_matching.py:130-227`) one-for-one, with **tax-id promoted to Pass 1** (customers have no tax-id; a matching EIN/SSN is near-certain identity) and **one deliberate, data-driven divergence** on the name tier (below).

Reuse verbatim: `STRONG_NAME=0.90`, `SUGGEST_NAME=0.60` (`:32-33`), and copies of `norm_email` (`:36-37`), `norm_phone` (`:40-43`), `_similarity` (`:50-54`). Add two helpers:
- `norm_taxid(raw) = re.sub(r'\D', '', raw)` (digits only, so `12-3456789` and `123456789` dedup).
- `hash_taxid(norm)` â†’ keyed HMAC (Â§4). `''` when no tax-id.
- `_vendor_name_key(v)` â€” an **enhanced** name key over `_name_key`: lowercase â†’ collapse punctuation to spaces â†’ collapse internal whitespace â†’ drop suffix/stop tokens `{inc, llc, co, corp, company, ltd, pa, cpa, the}` â†’ trim. This makes `The Pool Supply` / `Pool Supply` / `Pool Supply LLC` collapse and reliably surface each other as candidates. Feed this into `_similarity` for the vendor scorer (never mutates stored `Vendor.name`).

**Signature:**
```
resolve_vendor(session, *, source, external_id, name='', company='', tax_id='',
               email='', phone='', auto_create_when_new=True) -> VendorMatchResult
```
`VendorMatchResult` dataclass mirrors `MatchResult` (`:57-64`): `vendor_id: int|None`, `status`, `match_pass`, `confidence`, `created_vendor: bool`, `candidates: list`.

**Pass order:**

0. **O(1) short-circuit** (mirror `:143-153`): prior `VendorMatch` on `source_slug+external_id` with a set `vendor_id` â†’ return it, `created_vendor=False`. Repeat REFNUMs never re-run the passes.

1. Compute `nt=hash_taxid(norm_taxid(tax_id))`, `ne=norm_email(email)`, `np=norm_phone(phone)`. Load all `VendorProfile` once (mirror `_profiles` `:67-68`); **filter out `is_active=False`** (HIDDEN vendors excluded from auto-match, design Â§2.2).

2. **Pass 1 â€” exact tax-id.** If `nt` and any active `p.tax_id_hash == nt` â†’ upsert `status='auto'`, `match_pass=1`, `confidence=1.0`; `_enrich_vendor_profile`; return. *(Replaces email as the top key; a matching EIN/SSN is near-certain.)*

3. **Pass 2 â€” exact email.** `p.email == ne` â†’ `auto`, `match_pass=2`, `confidence=0.97`.

4. **Pass 2 â€” exact phone.** `p.phone == np` â†’ `auto`, `match_pass=2`, `confidence=0.95`.

5. **Pass 2 â€” strong fuzzy name/company.** Score every active profile `max(_similarity(name, display), _similarity(company, company_name))` using `_vendor_name_key`; sort descending.

6. **Candidate list** (mirror `:194-197`): profiles scoring `>= SUGGEST_NAME`, top 3, each `{vendor_id, name, score, reason:'name/company similarity'}`.

7. **Name-tier action â€” THE ONE VENDOR DIVERGENCE (documented, config-gated).** Constant `VENDOR_STRONG_NAME_AUTOLINKS = False`.
   - `resolve_customer` auto-links a `>=0.90` name match (`:186-192`). For **vendors** that is unsafe on this dataset: name is the *only* signal (0 tax-id/email, ~4 phones), and the real data contains genuine `>=0.90` false-positive pairs (`CIty of Key West` vs `KiA of Key West`; `Aivideo` vs `Invideo`). So with the flag `False`, an **uncorroborated** strong-name match (no exact tax-id/email/phone hit) is **not auto-merged** â€” it flows to Pass 3 as a possible-duplicate.
   - Setting the flag `True` restores the exact customer behavior (auto-link at `>=0.90`) for future sources that carry corroborating keys.

8. **Pass 3 â€” auto-attribute vs. queue** (mirror `:199-227`, "never orphan"):
   - candidates present **and** `auto_create_when_new` â†’ create its **own** new `Vendor`+`VendorProfile`, `status='flagged'`, `match_pass=3`, `confidence=candidates[0]['score']`, `created_vendor=True`. Rationale identical to `:199-203`: never wrongly merges two distinct vendors; worst case is a splittable duplicate a human resolves via `merge_vendor`.
   - candidates present, `auto_create` off â†’ `status='suggested'`, `vendor_id=None`, `match_pass=3` (manual queue).
   - no candidates, `auto_create` on (genuinely new) â†’ create vendor, `status='auto'`, `match_pass=1`, `confidence=1.0`, `created_vendor=True`.
   - else â†’ `status='unmatched'`, `match_pass=0`, `confidence=0.0`, `vendor_id=None`.

9. On any exact/strong match, `_enrich_vendor_profile` back-fills blank `tax_id_hash`/`tax_id_last4`/`email`/`phone` on the existing profile (mirror `_enrich_profile` `:114-127`).

**Companion functions** (copy shapes verbatim from `customer_matching.py`):
- `confirm_match(session, match_id, vendor_id)` â†’ `status='confirmed'` (mirror `:230-240`).
- `unlink_match(session, match_id)` â†’ clear `vendor_id`, `status='unmatched'`, `match_pass=0` (mirror `:243-254`).
- `list_matches(session, status=None, source=None)` â€” sorts `suggested`/`unmatched` first (mirror `:257-264`).
- `merge_vendor(session, from_vendor_id, into_vendor_id)` (mirror `merge_account` `:267-296`): no-op if equal; re-point the additive cost FKs (`ProductPriceHistory.vendor_id`, `ChemicalProduct.default_vendor_id`, `AssetRecord.vendor_id`, `CommercialVendorOrder.vendor_id`), re-point `ExternalIdentityMap` rows where `internal_type=='vendor'` and `internal_id==str(from)`, re-point `VendorMatch.vendor_id` (stamp `status='confirmed'`), delete the from-side `VendorProfile` + `Vendor`, single commit.
- `vendor_matching_summary(session)` (mirror `:299-312`): `total`, `by_status`, `needs_review = suggested + unmatched`, `possible_duplicates = flagged`, `vendors = count(VendorProfile)`.

---

## 3. `VendorListTranslator` (BaseTranslator subclass)

New `app/connectors/quickbooks/vendors.py`, mirroring `ChartOfAccountsTranslator` (`coa.py:111-167`) exactly. `BaseTranslator` contract confirmed at `base.py:75-98`; driver invariants (I1 verbatim-first, I2 no-silent-path, every row terminal) are owned by `run_translation` (`base.py:120-189`) â€” the subclass cannot break them.

```
class VendorListTranslator(BaseTranslator):
    source_slug = 'quickbooks'
    artifact_types = ('report_vendor_list',)   # standalone Vendor Contact List report
```

### 3.1 tokenize
Reuse the IIF tokenizer verbatim (`from app.connectors.quickbooks.iif import tokenize_iif`, `iif.py:27-69`), exactly as `coa.py:115-118`:
```
rows, encoding = tokenize_iif(raw_bytes); artifact.encoding_detected = encoding; return rows
```
**Then mark the sensitive cell:** iterate each row's cells and set `cell.is_sensitive = True` where `cell.header_name == 'TAXID'` (the tokenizer defaults `is_sensitive=False`, `iif.py:59` / `base.py:40`). This is what drives the `base.py` vault write (Â§4). On the real file this touches 0 cells (0 TAXIDs) but must exist for the next import.

### 3.2 classify (mirror `coa.py:120-133`, inverted for the VEND band)
- `row.band == 'VEND'` and `record_type == 'data'` â†’ `ClassifyResult(record_type='data', band='VEND')` (interpret).
- `record_type == 'header'` â†’ `skip_interpret`, reason `iif_header`.
- `record_type == 'blank'` â†’ `skip_interpret`, reason `blank`.
- `row.band == 'ACCNT'` â†’ `skip_interpret`, reason `handled_by_tier0_coa` (symmetric to coa.py's `deferred_to_tier2_vendors` `:129-130`).
- `row.band == 'HDR'` â†’ reason `iif_file_meta`.
- `row.band in ('CUSTNAMEDICT','CUSTITEMDICT')` â†’ reason `iif_list_dictionary`.
- else â†’ reason `not_a_vendor_list:{band or "unknown"}`.

Every non-VEND row is **retained** (RawSourceRow persisted) with an explicit terminal `excluded` status â€” nothing dropped.

### 3.3 interpret (mirror `coa.py:135-166`)
Build `d = {c.header_name: _unquote(c.raw_value) for c in cells if c.header_name}` (reuse `_unquote`, `coa.py:42-50`).

1. `raw_name = d.get('NAME','').strip()`. If empty â†’ `raise ValueError('VEND row missing NAME')` â†’ driver quarantines (`quarantined_parse`), never dropped (`base.py:176-178`). (0 blank-NAME rows in real data.)

2. **`not_a_trade_vendor` denylist** â€” a deterministic, owner-confirmable exact-NAME set (case-insensitive), the same override-dict pattern as `coa.py:81-85 CONFIRMED_ROLE_OVERRIDES`:
   `NON_VENDOR_NAMES = {'outgoing wire','wire transfer fee','unknown check','charge back','debit','eval','rent deposit'}`
   If `raw_name.lower()` in the set â†’ `return InterpretResult(status='excluded', reason='not_a_trade_vendor')`. No Vendor created; the raw row is retained. **Denylist only** (never a heuristic) so legitimate short/all-caps vendors (`USPS`, `FKAA`, `CVS`, `KFC`, `AFCO`, `chat GPT`) are preserved and matchable. ~7 rows in real data.

3. **Canonical display + person/company split** (data analysis Â§2, first non-empty wins):
   - `company = d.get('COMPANYNAME','').strip()`; `printas = d.get('PRINTAS','').strip()`
   - `person = ' '.join(x for x in [SALUTATION, FIRSTNAME, MIDINIT, LASTNAME] if x).strip()`
   - `display_name = company or printas or person or raw_name`
   - `is_individual = bool(person)` (extendable to a person-name pattern later). Store `person_name=person`.
   - **`Vendor.name = raw_name`** always (immutable key). When `display_name != raw_name`, set a note/reason so a human can confirm (guards the `AFCO`/`ACFO` transposition case).

4. `hidden = d.get('HIDDEN','').strip().upper() == 'Y'` â†’ `is_active = not hidden`. HIDDEN vendors are still created (no-loss, they are real vendors) but `is_active=False` excludes them from auto-match (design Â§2.2). Row status = `interpreted`. 0 in real data.

5. `is_1099 = d.get('1099','').strip().upper() == 'Y'` â†’ `VendorProfile.is_1099`. `True` also flags the vendor into the contractor-review filter and makes any TAXID required-sensitive. 0 in real data.

6. TAXID handling: the plaintext already went to the vault in the I1 phase (Â§4); interpret reads `tax_id_hash`/`tax_id_last4` from the persisted `RawSourceCell` (`is_sensitive` cell â†’ `value_hash`, and last-4 recomputed from the decrypt only if needed) rather than the blanked `raw_value`. Sets `VendorProfile.tax_id_hash`, `tax_id_last4`, and the `source_artifact_id`/`source_row_id` provenance pointer. 0 in real data.

7. Create `Vendor` + `VendorProfile`, then call `resolve_vendor(session, source='quickbooks', external_id=REFNUM or raw_name, name=raw_name, company=company, tax_id=..., email=d.get('EMAIL',''), phone=d.get('PHONE1',''))`. The resolver either links to an existing vendor (dedup) or attributes this one to its own vendor and flags possible duplicates. Emit `ExternalIdentityMap(entity_type='vendor', internal_type='vendor', internal_id=str(vendor_id))`.
   `return InterpretResult(status='interpreted')`.

Every VEND row is therefore terminal: `interpreted` (a Vendor), `excluded` (`not_a_trade_vendor`), or `quarantined_parse` (missing NAME). Post-condition `base.py:183-187` guarantees none left non-terminal.

### 3.4 Integration seams
- **Standalone Vendor Contact List report** (`artifact_type='report_vendor_list'`) â†’ normal full `run_translation` via the registry (`base.py:101-117`).
- **`!VEND` band inside `qb_lists.IIF`** â†’ run `VendorListTranslator` over the same bytes as its own `SourceArtifact`/`connector_run` (mirror how `test_quickbooks_coa.py:46-54` runs its translator standalone). ACCNT rows land `excluded:handled_by_tier0_coa` in this run; VEND rows interpret. The mild redundancy (two RawSourceRow sets for one 43 KB file) is acceptable and matches the framework's per-translator run model; a future optimization can share one tokenization across band-scoped translators.
- Register `quickbooks` as a source via existing `ensure_source_system` (already done for Tier 0); no `connector_tables.py` change.
- **Apply gate:** the `flagged`/`auto` writes ride the same approval gate as Tier 1 `ExpenseActual` â€” `approve_communication`/`ApprovalDecision`/`ApplyEvent` (`front_desk.py:1414`, design Â§4.5 item 13). Do **not** direct-write.

---

## 4. PII HANDLING (TAXID)

Real data has **0 TAXIDs**, so this path is **dormant for Tier 2's actual run** â€” but it must ship wired, because (a) the translator marks `TAXID` cells `is_sensitive=True`, and (b) the moment a sensitive cell exists, `base.py:152` would blank `raw_value` and write nothing to the vault â†’ the value is *lost*, violating no-loss. Wiring the vault is therefore a required Tier-2 fix, not a future nicety.

### 4.1 Add `cryptography` (Fernet) â€” recommended
- `requirements.txt` (`:1-13`, currently no crypto): add `cryptography>=44.0`. The venv already ships far heavier wheels (pandas, openpyxl, streamlit); one supported dependency beats hand-rolled crypto.
- New `app/core/secrets.py`:
  - `encrypt(plaintext) -> str = Fernet(key).encrypt(plaintext.encode()).decode()` (Fernet = AES-128-CBC + HMAC-SHA256, tamper-evident).
  - `decrypt(token) -> str = Fernet(key).decrypt(token.encode()).decode()`.
  - `keyed_hash(normalized) -> str = hmac.new(pepper, normalized.encode(), hashlib.sha256).hexdigest()`.
- `config.py` (`:1-25`, no secret today): add `UPS_FIELD_ENCRYPTION_KEY` (32-byte url-safe base64 Fernet key) and `UPS_TAXID_HASH_PEPPER`, both from env. **Keys live outside the SQLite file** (env/secret store) â€” the DB holds only ciphertext + keyed hash, or "encrypted at rest" is meaningless. Not in git.

### 4.2 `value_hash` must be a keyed HMAC, not a bare/salted digest
Flag the design doc wording: `RawSourceCell` in Â§1.2 and Â§6.12 say "salted hash". An EIN/SSN is a ~9-digit space (~10â¹) â€” a bare or per-row-salted SHA-256 is trivially enumerable and gives no confidentiality for dedup. Use `keyed_hash(norm_taxid)` with a server-side pepper (attacker needs the pepper to enumerate). Normalize first (`norm_taxid`, digits only) so `12-3456789` and `123456789` dedup.

### 4.3 The `base.py` fix (required, minimal, backward-compatible)
Extend the cell-persist loop `base.py:146-157`. Today `:152` is `raw_value='' if c.is_sensitive else c.raw_value` with `cipher_value`/`value_hash` never set. Change so that when `c.is_sensitive`:
- `cipher_value = encrypt(c.raw_value)`
- `value_hash = keyed_hash(norm_taxid(c.raw_value))`
- then blank `raw_value` (unchanged for the sensitive case).

Non-sensitive cells take the existing `else c.raw_value` path unchanged â€” nothing else is affected. **Fail-loud gate:** if a sensitive cell arrives while `UPS_FIELD_ENCRYPTION_KEY` is unset, quarantine the row (`quarantined_parse`, reason `sensitive_field_no_key`) rather than silently drop â€” no-loss preserved by refusing, not discarding.

### 4.4 What appears in query/review surfaces
Only: `display_name`, `company_name`, `terms`, `is_1099`, `vendor_type`, `address_block`, `email`, `phone`, and **TAXID masked as `**-***{last4}`** â€” never plaintext (design Â§4.5 item 15, validation Â§6.12). Full TAXID is recoverable **only** via `decrypt(RawSourceCell.cipher_value)` inside the gated apply/review path (design Â§1.2 "decrypt only inside the gated apply/review path"), gated the same way as `approve_communication` (`front_desk.py:1414`).

### 4.5 Stdlib-only fallback (if `cryptography` is refused) â€” a downgrade, recommend against
Python stdlib has no symmetric cipher. Least-bad: scrypt KDF (`hashlib.scrypt`) from an env KEK â†’ HMAC-SHA256 keystream CTR-mode by hand â†’ encrypt-then-MAC with an HMAC-SHA256 tag â†’ store `base64(nonce||ct||tag)` in `cipher_value`, verify with `hmac.compare_digest`. `value_hash` = same keyed HMAC. This is real but hand-rolled; given the platform already ships dozens of wheels, add `cryptography` instead. Either way the key/pepper enter `config.py` and stay out of the DB and git.

---

## 5. TEST PLAN

### 5.1 Unit â€” `tests/test_vendor_matching.py` (synthetic, in-memory SQLite; mirror `test_customer_matching.py:16-19` `_session()`)
- `test_pass1_exact_taxid_autolinks` â€” two records, same TAXID, different names â†’ `auto`, `match_pass=1`, same `vendor_id`, no duplicate `Vendor`. (Vendor-specific top key.)
- `test_pass2_exact_email_autolinks` / `test_pass2_exact_phone_autolinks` â€” mirror `test_customer_matching.py:27-51`.
- `test_name_only_match_flags_not_merges` â€” **the divergence.** Seed `Premier Painting`; resolve `Premier Paitning` (no tax-id/email/phone) â†’ `status='flagged'`, `match_pass=3`, its own `vendor_id`, `candidates[0].vendor_id == seed`, **2 Vendors**, asserts it did **not** auto-link. (Contrast `test_customer_matching.py:53-65`.)
- `test_new_vendor_no_match_creates` â€” mirror `:68-75`.
- `test_manual_confirm_and_override_persists` â€” confirm then re-resolve returns `confirmed`; unlink re-queues `unmatched` (mirror `:78-97`).
- `test_merge_vendor_repoints_and_removes_source` â€” put a `ProductPriceHistory` row with `vendor_id=from`; `merge_vendor` moves it, re-points `ExternalIdentityMap` (`internal_type='vendor'`) + `VendorMatch`, deletes from-side profile+vendor; `possible_duplicates` 1â†’0 (mirror `:100-121`).
- `test_short_circuit_on_prior_map` â€” second resolve of the same `source+external_id` after a link returns `created_vendor=False` and re-runs nothing (asserts `:143-153` behavior; e.g. patch `_profiles` to raise, prove it isn't called).
- `test_hidden_vendor_excluded_from_automatch` â€” inactive profile is never a candidate even at an exact-name overlap.
- `test_taxid_never_plaintext` â€” after a resolve with a tax-id: `VendorProfile` has no plaintext field; `tax_id_hash != raw`; `tax_id_last4` correct; `decrypt(RawSourceCell.cipher_value)` round-trips.
- `test_vendor_matching_summary` â€” `needs_review == suggested+unmatched`, `possible_duplicates == flagged`, `vendors == count(VendorProfile)`.

### 5.2 Translator â€” `tests/test_quickbooks_vendors.py` (synthetic IIF fixture; mirror `test_quickbooks_coa.py`)
Fixture: CRLF, full `!VEND` header, then rows exercising every branch â€” a plain vendor, a `COMPANYNAME` override, a person (FIRST/LAST) vendor, a `HIDDEN=Y` vendor, a `1099=Y` vendor **with a TAXID** (exercises the sensitive/vault path the real file can't), an `OUTGOING WIRE` placeholder, a near-duplicate pair, plus an `!ACCNT` band, `!HDR`, and a trailing blank. Encode `cp1252` (mirror `test_quickbooks_coa.py:26-43`).
- `test_byte_anchored_round_trip_holds_with_crlf` â€” I1, slice original bytes decode back (mirror `:57-62`).
- `test_vend_data_rows_become_vendors` â€” count + names.
- `test_companyname_override_display_name` â€” `display_name == COMPANYNAME`, `Vendor.name == raw NAME` (key unchanged).
- `test_person_vendor_uses_person_name` â€” `person_name` set, `is_individual` true.
- `test_hidden_vendor_created_inactive_and_excluded` â€” `is_active=False`, not an auto-match candidate, row `interpreted`.
- `test_1099_taxid_cell_encrypted_not_plaintext` â€” `RawSourceCell.raw_value == ''`, `cipher_value != ''`, `value_hash != ''` (proves the `base.py:152` fix); `VendorProfile.tax_id_last4`/`tax_id_hash` set; `is_1099 == True`.
- `test_not_a_trade_vendor_excluded_with_reason` â€” `OUTGOING WIRE` row `status=='excluded'`, reason `not_a_trade_vendor`, **no Vendor** created.
- `test_near_duplicate_flagged` â€” the pair yields a `flagged` possible-duplicate, not an auto-merge.
- `test_accnt_and_headers_retained_but_excluded` â€” `!ACCNT` data â†’ `excluded:handled_by_tier0_coa`; headers â†’ `iif_header`; blank â†’ `blank` (mirror `:108-115`).
- `test_every_row_reaches_terminal_status` â€” all rows in `{interpreted, excluded, superseded, quarantined_parse}` (mirror `:118-122`).

### 5.3 Real-data validation â€” `tests/test_vendor_real_data.py` against `data/imports/quickbooks/qb_lists.IIF`
- **Every row terminal, none dropped:** all 357 `!VEND` data rows reach a terminal status; RawSourceRow count == physical VEND lines.
- **Every vendor resolves/excludes with a reason:** each VEND row is `interpreted`â†’Vendor or `excluded`â†’`not_a_trade_vendor`; assert the ~7 known placeholders (`OUTGOING WIRE`, `Wire transfer Fee`, `Unknown Check`, `charge back`, `debit`, `EVAL`, `rent Deposit`) are excluded, and that legit short vendors (`USPS`, `FKAA`, `CVS`, `KFC`, `AFCO`) are **kept**.
- **~350 Vendors created**, all with a non-empty immutable `Vendor.name`.
- **No PII leak:** every `VendorProfile.tax_id_hash == ''` and `tax_id_last4 == ''` (0 TAXIDs present); `email == ''` for all (0 emails); nothing plaintext anywhere; `list_matches`/`vendor_matching_summary` output contains no sensitive field.
- **HIDDEN branch dormant:** assert 0 inactive vendors (0 HIDDEN=Y) â€” branch exercised by the synthetic fixture only.
- **Dedup surfaced, nothing auto-merged:** `possible_duplicates > 0`; assert a known typo pair (`Premier Painting`/`Premier Paitning`, or `Menendez`/`Mendez Mobil Auto Service`) appears as `flagged` candidates; assert **distinct NAMEs never silently collapse** into one Vendor.
- **False-positive guard:** `CIty of Key West` vs `KiA of Key West`, and `Aivideo` vs `Invideo`, resolve to **distinct** Vendors (never auto-merged) â€” this is what `VENDOR_STRONG_NAME_AUTOLINKS=False` buys.
- **Idempotency:** all 357 REFNUMs unique â†’ unique `external_id`s; a second run produces **0 new Vendors** (short-circuit at Â§2 step 0).

---

## 6. EXPLICIT SCOPE NOTE

**`qb_lists.IIF` contains no items â€” 0 item/material unit costs.** The export carries bands `!HDR, !ACCNT, !VEND, !CUSTNAMEDICT, !CUSTITEMDICT`; there is **no `!INVITEM` band**. QuickBooks item unit costs are therefore not present in this file at all.

Consequently:
- The design's Tier 2 has two halves â€” vendors **and** item/material unit costs (design Â§5, Tier 2: "`!VEND` â†’ Vendor; Item Listing (with Cost)/`!INVITEM` â†’ `ChemicalProduct.default_unit_cost`"). **This spec delivers only the vendor half.**
- The **chemical-cost unlock is deferred.** Chemical unit cost silently reads `0.0` today (`profitability.py:104`, `variance.py:217`) and stays that way until either (a) a separate *Item Listing (with Cost)* report export is ingested, or (b) **Tier 3** line-level bills (`!TRNS`/`!SPL` `BILL`/`CHECK`/`CCARD`) land dated per-vendor unit costs via `create_price_history` (`expenses.py:32-48`), feeding `latest_unit_cost` (`expenses.py:23`).
- Tier 2 as scoped delivers the **vendor identity spine only**: `Vendor`/`VendorProfile`/`VendorMatch` + `resolve_vendor` + `VendorListTranslator` + the TAXID vault + the additive nullable `vendor_id` columns. **Tier 3 bills reference `vendor_id`** â€” the spine is Tier 3's prerequisite (design: "Tier 3 Depends: Tier 2").
- Also out of Tier-2 apply scope: **backfilling `vendor_id` onto existing cost rows** and rewriting `purchasing.py`'s string grouping (`purchasing.py:81,144`). Tier 2 adds the nullable columns (additive, breaks nothing); linking live cost rows to a canonical `vendor_id` is a later change on live tables. The HIDDEN / 1099 / TAXID branches are all built and tested but **dormant on this file** (0 rows each).