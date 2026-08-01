# QuickBooks Universal Translator: No-Loss Ingestion Design (FINAL / canonical)

**Lumen / POLR R&D | Unified Pool Service Platform | Cost & Profitability Ingestion**

**Repo root:** `C:/Users/krist/Desktop/unified_pool_service_platform_build/unified_pool_service_platform_build`
**Scope:** Design only. No code to apply. QuickBooks is the first source plugged into a reusable universal-translator skeleton; every later source (bank feeds, payroll processors, insurance statements) plugs into the same skeleton.
**Status:** Supersedes the prior draft. Every adversarial-review finding (#1â€“#30) is resolved in-line and annotated `(resolves #N)`. A finding-coverage matrix closes the document.

---

## How this guarantees nothing is discarded

- **Every byte survives before any parse.** File bytes go to `UPLOAD_DIR` untouched with a `file_sha256`; every logical record is stored verbatim in `RawSourceRow.raw_line_text` **with its start:end byte offsets**, so the round-trip is anchored to raw bytes, not a re-decode that could hide a mojibake (resolves #8). If the derived tables were dropped, the entire import rebuilds from bytes + rows alone.
- **Every row terminates in exactly one queryable status â€” including on failure.** `classify()`/`interpret()` run inside a per-row try/except; a thrown exception writes `quarantined_parse` + traceback and continues. A hard post-condition asserts interpretation-record count == `RawSourceRow` count, so no exception, skip, or `continue` can drop a row (resolves #15; bans the `skimmer_sync.py:226` pattern).
- **Meaning is validated, not just bytes.** Cells are re-serialized and must reconstruct `raw_line_text`; every data row's cell count must equal the active header width or it quarantines; each band's parsed money column must cross-foot to that band's captured `Total` control row as a hard gate (resolves #7).
- **No dollar is counted twice.** Cost has a single source of truth elected per `(account, period, basis)`: labor and payroll accounts live only in `LaborSettings`/`PayrollRun` (never in overhead), IIF line detail supersedes report totals for the same cell, depreciation reconciles to (never adds onto) its expense account, and parent-including-subaccount roll-ups are a distinct non-summed class (resolves #1â€“#5).
- **Money is understood by TYPE and normal balance, in `Decimal`.** A dollar's meaning comes from `account_type` + normal-balance sign rule + dimensions, never column position or display name. All money is `Decimal`; tie-outs use exact-zero intra-file and an explicit Â±tolerance cross-export (resolves #9, #29).
- **Revenue, money-movement, capital, voids, and PII-bearing masters are refused for coded, visible reasons â€” not deleted.** Every exclusion/quarantine is persisted, reason-coded, reversible, and surfaced in a review queue. SSN/TaxID bytes are preserved encrypted-at-rest so no-loss holds without leaking PII into query surfaces (resolves #19, #28).
- **Nothing applies except through a gated, reversible, reconciled path** â€” and the un-applied backlog is made loud: the sign-off gate shows "cost-per-hour excludes $X (Y%) still in review" and refuses "live" while un-applied cost exceeds threshold, so a review backlog can never silently deflate the cost number (resolves #11, #16).
- **Idempotency survives real re-exports.** `file_sha256` catches only identical re-uploads; a composite natural transaction key (date+docnum+account+amount+memo+line-ordinal) dedups re-exports where QuickBooks restamps the `!HDR` timestamp and leaves `TRNSID` blank (resolves #23, #24).

---

## Owner mandate, restated as engineering invariants

The mandate ("not one line or word discarded; understand before applying; QuickBooks is the best factual base we will ever have") becomes five hard invariants:

1. **I1 â€” Verbatim first.** Untouched bytes of every file, and untouched text of every row and cell, are stored and byte-addressable *before* any parse. The parse is a derived, disposable projection, never a replacement.
2. **I2 â€” No silent path.** Every raw row terminates in an explicit, queryable status. No `continue`/skip drops a row; even an interpreter exception lands the row in quarantine (the `skimmer_sync.py:226` `unmatched_work_orders += 1; continue` pattern is banned).
3. **I3 â€” Understand by TYPE, not by column.** A dollar's meaning comes from `account_type`, normal-balance sign, and dimensions â€” never column position or display name.
4. **I4 â€” Apply only through a gate.** Nothing writes to a cost target except through an approval-gated `ApplyEvent`, following the `approve_communication` template (`app/services/front_desk.py:1414`), never the ungated direct-write of `app/services/freshbooks_revenue.py`.
5. **I5 â€” Count once (new).** Every dollar on a QuickBooks statement lands in exactly one cost bucket, under exactly one elected source of truth per `(account, period, basis)`, and the buckets must close to `Net Income`. No account may feed two cost targets.

---

## 1. NO-LOSS ARCHITECTURE

### 1.1 The problem with today's raw layer

The platform already has a verbatim raw store, but at the wrong grain and used on only two of four paths:

- `RawSourceRecord.payload_json` (`app/models/connector_tables.py:41`) stores an inbound dict verbatim with a sha256 (`app/services/ingestion.py:57`). Good, but **dict grain** â€” it assumes clean records. QuickBooks hands you *files* (IIF, CSV, XLSX) whose rows are banded, interleaved, position-dependent.
- `InvoiceLineStaging.raw_line_text` (`app/models/tables.py`) stores one verbatim line per invoice line (`app/services/invoice_ingestion.py:99`) â€” closest to line-level no-loss, but PDF-invoice-specific.
- `app/services/freshbooks_revenue.py` writes **no** raw row at all. This path must never be the template.

QuickBooks needs a store one level lower: **file â†’ row â†’ cell**, positional, byte-addressed, immutable.

### 1.2 Immutable tables (the verbatim spine)

Design only; these sit alongside `connector_tables.py`, generalized so any file-based source reuses them.

**`SourceArtifact`** â€” one row per uploaded export file (generalizes `InvoiceDocument`, `app/models/tables.py:270`).

| Field | Purpose |
|---|---|
| `id`, `source_slug` | e.g. `quickbooks` |
| `artifact_type` | `iif` \| `report_gl` \| `report_pnl_detail` \| `report_txn_detail` \| `report_coa` \| `report_vendor_list` \| `report_item_list` \| `report_payroll_summary` |
| `original_filename`, `file_path` | bytes stored untouched under `UPLOAD_DIR` (pattern of `invoice_ingestion.py:30`) |
| `file_sha256`, `byte_size` | integrity anchor for I1 and identical-reupload idempotency |
| `encoding_detected`, `encoding_confidence` | `windows-1252` vs `utf-8` (QB exports are usually CP-1252; hazard #18). **On any decode that yields a U+FFFD replacement char or a byte sequence that does not round-trip through the chosen codec, the artifact is set `status = quarantined_artifact`, reason `encoding_failure`, and ingest of that artifact stops before row creation** (resolves #8) |
| `basis` | `accrual` \| `cash` \| `unknown` â€” **first-class dimension** parsed from the report title block or IIF, stamped onto every fact derived from this artifact (resolves #26) |
| `date_locale` | `MDY` \| `DMY` \| `ambiguous` â€” derived from the title-block date range and cross-checked against values (resolves #27) |
| `report_meta_json` | captured title-block rows (company, report title, date range, basis) and IIF `!HDR` record â€” preserved, not discarded |
| `connector_run_id`, `imported_at`, `imported_by`, `status` | lifecycle (`status âˆˆ pending \| parsed \| reconciled \| live \| quarantined_artifact`) |

**`RawSourceRow`** â€” one row per physical/logical record, verbatim. The canonical no-loss unit.

| Field | Purpose |
|---|---|
| `id`, `artifact_id`, `connector_run_id`, `source_slug` | |
| `row_index` | 0-based position; the permanent address of this row |
| `byte_offset_start`, `byte_offset_end` | **byte span of this record in the original file** â€” makes the Â§6 round-trip byte-anchored, not decode-anchored (resolves #8) |
| `physical_line_span` | start:end physical line numbers (a logical record can span several physical lines when a quoted memo has embedded newlines â€” hazards #16, #27) |
| `raw_line_text` | the entire original record, byte-exact after encoding decode, quotes/tabs/`$`/parentheses/middle-dot all preserved |
| `row_sha256` | dedup + tamper check |
| `classification` | set by the classifier: `title` \| `blank` \| `band_header` \| `beginning_balance` \| `transaction` \| `subtotal` \| `subtotal_parent_rollup` \| `total` \| `payroll_component` \| `payroll_subtotal` \| `iif_header` \| `iif_trns` \| `iif_spl` \| `iif_endtrns` \| `iif_list` \| `unknown`. **`subtotal_parent_rollup`** is the `Total <Parent> including subaccounts` row; it is never summed into facts and never used as a leaf tie-out target (resolves #5) |
| `status` | terminal lifecycle status (Â§3) â€” never null, never skipped |

`raw_line_text` is the source of truth. If every derived table were dropped, the full import rebuilds from `SourceArtifact` bytes + `RawSourceRow` alone. That is the concrete meaning of I1.

**`RawSourceCell`** â€” one row per cell; the addressable projection (satisfies "not one word").

| Field | Purpose |
|---|---|
| `id`, `raw_row_id`, `artifact_id`, `col_index` | address = `(artifact_id, row_index, col_index)`, stable forever |
| `col_header_label` | the header this column fell under, or `''` for QB's unlabeled grouping column (hazard #2) |
| `raw_value` | verbatim cell string, including `$`, thousands commas, `(parentheses)`, trailing-minus, `%`, `10100 Â· Checking` middle-dot â€” normalization happens downstream |
| `value_was_quoted` | whether the source quoted the field (drives embedded-newline handling) |
| `is_sensitive`, `cipher_value`, `value_hash` | **for designated sensitive fields (SSN `SSNO`, `TAXID`), `raw_value` holds the tokenized/ciphertext, `cipher_value` the encrypted-at-rest blob, `value_hash` the salted hash used for byte round-trip and dedup.** No-loss holds (the value is recoverable) without leaking PII into every query surface (resolves #19) |

Cells are a derived index; always re-derivable from `raw_line_text` (sensitive cells re-derive to ciphertext + hash, and decrypt only inside the gated apply/review path).

### 1.3 Re-parse, rollback, idempotency, integrity

- **Re-parse:** delete all interpretation/normalized rows for an `artifact_id` and rebuild from `RawSourceRow`. The verbatim spine is immutable, so re-parse is lossless. **Re-parse is BLOCKED while any `ApplyEvent` exists against the artifact** (deleting applied normalized rows would orphan `ApplyEvent`/`ExternalIdentityMap`). To re-parse an applied artifact, the run's applies are rolled back first (below), *or* re-linking is done by natural key so rebuilt rows re-attach deterministically. A regression test asserts **re-parse-after-apply produces zero new applies** (resolves #24).
- **Rollback of an apply:** applies are an append-only ledger (`ApplyEvent`, `connector_tables.py:80`) keyed to a `connector_run_id`. Rollback walks the run's `ApplyEvent` rows and reverses each target write (or marks it superseded). `ExternalIdentityMap` (`connector_tables.py:91`) gives idempotency so re-apply after a fixed parse never duplicates.
- **Idempotency that survives real re-exports:** `file_sha256` catches only **identical re-uploads**. QuickBooks restamps `!HDR` DATE/TIME on every export, so a re-export of the same period is byte-different and `file_sha256` will not dedup; and IIF `TRNSID`/`SPLID` are frequently blank. Therefore every transaction carries a **composite natural key** = `sha256(basis + txn_date + docnum + account_code + amount + memo + line_ordinal)`; `ExternalIdentityMap.external_id` uses `TRNSID/SPLID` when present else this composite. Dedup and re-link are keyed on it (resolves #23, and enables the deterministic re-parse re-link of #24).
- **A row is never lost even if unmapped:** every `RawSourceRow` gets exactly one interpretation record with a terminal status. Unmapped account â†’ `quarantined_unmapped`; excluded revenue â†’ `excluded_by_type`; interpreter crash â†’ `quarantined_parse`. There is no code path that reads a row and produces nothing (I2; audit Â§3, Â§5.3).
- **Periodic byte integrity sweep (new):** a scheduled job re-hashes every `SourceArtifact.file_path` against its stored `file_sha256` and alarms on mismatch or missing file, so the rebuild-from-bytes guarantee cannot die silently if a file is later moved or corrupted (resolves #25). Registered as a cron alongside the connector runs.

---

## 2. FIELD-BY-FIELD MAPPING

Rule for the whole section: **every source column is `MAP` (drives a target field), `CTX` (carried as context/dimension, not itself a dollar), or `QUAR` (quarantined with a reason).** Nothing is silently dropped. Sign handling: on `COGS`/`EXP`/`EXEXP` accounts, **signed-net, positive = cost incurred, negative = cost reduction; negatives are preserved, never dropped or absolute-valued.** All money parses to `Decimal` (resolves #9).

Target fields: `ExpenseItem.annual_cost` (`app/models/tables.py:13`), `LaborSettings` (`app/services/estimator.py:16`, stored as `SystemSetting` key `labor_settings`), `ChemicalProduct.default_unit_cost` (`tables.py:22`), `ProductPriceHistory.unit_cost` (`tables.py:37`), and the new tables from Â§4 (`Vendor`, `Bill`/`BillLine`, `LedgerAccount`, `ExpenseActual`, `Employee`/`PayrollRun`, `CompanyAsset`).

### 2.1 IIF `!ACCNT` â€” Chart of Accounts (the type dictionary; ingest FIRST)

| Column | Disposition | Target / handling |
|---|---|---|
| `NAME` | MAP | `LedgerAccount.name`; split `Parent:Child` on colon into hierarchy (hazard #30). **If a colon-split yields a parent segment not already present in ingested masters, do NOT auto-create a phantom parent â€” set the row `needs_review`, reason `ambiguous_hierarchy`** (resolves #30) |
| `ACCNTTYPE` | MAP | `LedgerAccount.account_type` â€” the most important field (I3). Enum `BANK/AR/AP/OCASSET/FIXASSET/OASSET/OCLIAB/LTLIAB/EQUITY/INC/EXP/COGS/EXINC/EXEXP/NONPOSTING`. Drives the whole cost filter and the normal-balance sign rule (Â§2.6) |
| â€” (derived) | MAP | `LedgerAccount.normal_balance` = `debit` for `COGS/EXP/EXEXP/FIXASSET/OCASSET/OASSET/AR/BANK`, `credit` otherwise. Used by the GL sign rule (resolves #29) |
| â€” (derived) | MAP | **`LedgerAccount.is_labor_account`** â€” set when the account is a wages/salary/payroll-tax/benefit account (name-keyword + owner confirmation). Guarantees a payroll account can never land in `annual_overhead_total` (resolves #1, #4) |
| â€” (derived) | MAP | **`LedgerAccount.is_depreciation_account`** â€” set for depreciation-expense accounts, so Tier 5 reconciles rather than re-adds (resolves #3) |
| `ACCNUM` | MAP | `LedgerAccount.account_code` (present only if account numbers enabled) |
| `DESC` | CTX | `LedgerAccount.description` |
| `OBAMOUNT` | CTX | opening balance; not a period cost, carried for reconciliation |
| `REFNUM`, `TIMESTAMP`, `BANKNUM`, `EXTRA` | CTX | stored on the account row |
| `HIDDEN`, `DELCOUNT` | CTX + gate | active/inactive flag; **`HIDDEN=Y` accounts are excluded from auto-match and routed to review so an inactive account can't fuzzy-match a live one** (resolves #18) |

### 2.2 IIF `!VEND` / Vendor Contact List â€” Vendors (build target first, Â§4)

| Column | Disposition | Target |
|---|---|---|
| `NAME`, `COMPANYNAME`, `PRINTAS` | MAP | `Vendor.name` / `display_name` |
| `SALUTATION`, `FIRSTNAME`, `MIDINIT`, `LASTNAME` | MAP (fallback) | `Vendor.person_name`; **when `COMPANYNAME` is blank, `FIRSTNAME`+`LASTNAME` is the resolution key** (a vendor that is a person, not a company) (resolves #18) |
| `TERMS` | MAP | `Vendor.terms` |
| `TAXID` | MAP (sensitive) | `Vendor.tax_id` â€” **designated sensitive: stored encrypted-at-rest with hash for round-trip** (resolves #19) |
| `1099` | MAP | `Vendor.is_1099` |
| `ADDR1..5` / report `Bill from` | CTX | `Vendor.address_block` â€” keep as one multi-line block (hazard #16) |
| `PHONE1/2`, `FAXNUM`, `EMAIL`, `CONT1/2` | CTX | contact fields |
| `VTYPE` | CTX | vendor category |
| `NOTE`, `NOTEPAD` | CTX | preserved verbatim (resolves #18) |
| `LIMIT`, `Balance Total` | CTX | open A/P; carried, **not** ingested as cost (A/P is a liability, Â§3) |
| `CUSTFLD1..15` | CTX | custom fields preserved verbatim |
| `HIDDEN`, `DELCOUNT` | CTX + gate | inactive vendors excluded from auto-match, routed to review (resolves #18) |

Vendor resolution uses `resolve_vendor` (generalized `resolve_entity`) with the same thresholds as `customer_matching.py` (`STRONG_NAME = 0.90`, `SUGGEST_NAME = 0.60`, `customer_matching.py:32-33`); `ExternalIdentityMap` carries `entity_type='vendor'`.

### 2.3 IIF `!CUST` â€” Customers (reuse existing spine)

`NAME`/`COMPANYNAME`/`EMAIL`/`PHONE1`/`BADDR*` â†’ `resolve_customer` (`app/services/customer_matching.py`) â†’ `Account` + `CustomerProfile`. `SADDR*` (ship-to) is now **explicitly CTX** (prior draft omitted it) â€” carried as a dimension, never dropped (resolves #18). Colon names are `Customer:Job` (hazard #30); the same `ambiguous_hierarchy` review path as Â§2.1 applies. `TERMS`, `TAXITEM`, `CUSTFLD*`, `NOTE` â†’ CTX.

### 2.4 IIF `!INVITEM` / Item Listing (with Cost) â€” Items â†’ chemical/material costs

| Column | Disposition | Target |
|---|---|---|
| `NAME` | MAP | match to `ChemicalProduct.sku`/`name`/aliases via `best_match` (`app/utils/matching.py`, as `invoice_ingestion.py:88`) |
| `COST` | MAP | `ChemicalProduct.default_unit_cost` (`tables.py:22`). **If the cell contains `%` (discount/markup items), it never reaches the numeric parser â€” the item is excluded (below)** (resolves #21) |
| `PREFVEND` | MAP | `ChemicalProduct.default_vendor` (`tables.py:25`) â†’ FK to `Vendor` |
| `COGSACCNT` | MAPâ†’CTX | confirms COGS-typed; carried as the account link |
| `INVITEMTYPE` | MAP â†’ routing | `SERV/NONINVPART/OTHC` â†’ cost at purchase; **`INVENTORY` (perpetual)** â†’ QUAR note, pull COGS at consumption not asset build (semantics Â§6b, must-exclude #13); **`DISC/SUBT/GROUP/PMT/STAX`** â†’ `excluded_by_type`, reason `non_cost_item_type` (no cost account; keeps them out of `quarantined_unmapped`) (resolves #21) |
| `DESC`, `PURCHASEDESC`, `MPN`/`EXTRA` | CTX | `manufacturer_part_number`, description |
| `TAXABLE`, `SALESTAXCODE`, `DEP_TYPE` | CTX | preserved verbatim (resolves #18) |
| `PRICE`, `ACCNT` (income) | CTX | sales side; carried, **never ingested as cost** (Â§3 double-count guard) |
| `ASSETACCNT`, `QNTYONHAND`, `REORDERPOINT` | CTX | inventory metadata (target gap B.8) |
| `CUSTFLD1..5` | CTX | preserved verbatim (resolves #18) |
| `HIDDEN`, `DELCOUNT` | CTX + gate | `HIDDEN=Y` items excluded from auto-match, routed to review (resolves #18) |

### 2.5 IIF `!TRNS` / `!SPL` / `!ENDTRNS` â€” the transaction ledger (the cost facts)

Cost dollars come from here. **IIF is preferred over report exports** â€” reports print `-SPLIT-` and lose offsetting accounts (hazard #12); IIF preserves double-entry. Parse as blocks: `TRNS` + NÃ—`SPL` + `ENDTRNS` (hazard #28), tracking the active `!`-header layout per keyword (hazard #25). **Block-structure failures are quarantined, never dropped or halted** (see Â§3.1 reasons; resolves #13, #14).

Per split line, disposition depends on the **account type resolved from Â§2.1**:

| `SPL`/`TRNS` column | Disposition | Handling |
|---|---|---|
| `ACCNT` | MAP | join to `LedgerAccount` â†’ `account_type` + `normal_balance` + `is_labor_account`. Type decides everything below. |
| `AMOUNT` | MAP (if cost type) | signed `Decimal`, no symbols (IIF debit-positive/credit-negative). On `COGS`/`EXP`/`EXEXP`: positive = cost, negative = cost reduction, net, preserve sign. **Per block, assert `TRNS.AMOUNT + Î£SPL.AMOUNT == 0` exactly (Decimal); on failure quarantine the ENTIRE block, reason `iif_block_unbalanced` â€” never apply an imbalanced block, never halt the batch** (resolves #13). **`AMOUNT == 0` or memo prefixed `VOID:`/`VOIDED` â†’ `excluded_by_type`, reason `voided_or_zero`; never writes unit cost** (resolves #28). |
| `TRNSTYPE` | MAP/QUAR | `BILL`/`CHECK`/`CCARD` cost lines â†’ ingest. `BILLPMT`/`TRANSFER`/CC-payment/`LIABCHECK` â†’ `excluded_money_movement` even on a cost account (must-exclude #5,6,8). `GENERAL JOURNAL` cost account paired only to a balance-sheet account â†’ `needs_review`. `PAYCHECK` â†’ payroll Â§2.7. |
| `CLASS` | CTX | route/service-line dimension â†’ `class_tag` (semantics Â§3; target gap B.7) |
| `NAME` | CTX | vendor or `Customer:Job` â†’ per-route/per-customer dimension |
| `INVITEM` | CTX | item tag (descriptive; the GL account is the fact â€” do not sum both, must-exclude #15) |
| `QNTY`, `PRICE` | MAP (guarded) | on a chemical COGS line â†’ **`ProductPriceHistory.unit_cost = abs(AMOUNT) / abs(QNTY)` computed only when `QNTY` is present and non-zero; when `QNTY` is null/0, route to `needs_review`, reason `unit_cost_no_qnty` â€” never write a 0 or inf, never let a negative QNTY flip cost negative** (resolves #6). `effective_date = DATE` (`tables.py:34-38`) |
| `DATE` | MAP | transaction date â†’ `Bill.date` / `ProductPriceHistory.effective_date`. **Parsed per `SourceArtifact.date_locale`; a value that is ambiguous under the elected locale (e.g. day â‰¤ 12 with no disambiguator when locale is `ambiguous`) â†’ `needs_review`, reason `ambiguous_date_locale`** (resolves #27) |
| `DOCNUM` | MAP | `Bill.ref_number` / `ProductPriceHistory.invoice_number`; feeds the composite natural key (Â§1.3) |
| `MEMO` | CTX | free text (may contain embedded newlines â€” hazard #27) |
| `DUEDATE`, `TERMS`, `PONUM` | CTX | on `Bill` |
| `CLEAR`, `TOPRINT`, `PAID`, `ADDR*`, `SADDR*`, `REP`, `FOB`, `SHIPVIA` | CTX | preserved on raw + bill row |
| `SPLID`/`TRNSID`, `VALADJ`, `REIMBEXP`, `YEARTODATE`, `WAGEBASE`, `OTHER2/3` | CTX | preserved verbatim; not cost inputs (`TRNSID`/`SPLID` feed identity when present, Â§1.3) |

Target for cost splits: **new `Bill` + `BillLine`** (mirror `BillingDocument`/`BillingLine`, `ops_tables.py:9-27`, this time populating `raw_json`), plus `ProductPriceHistory` for chemical unit costs, plus aggregation into `ExpenseActual` for overhead accounts. **Labor/payroll-typed accounts (`is_labor_account`) never write `Bill`/`ExpenseActual` overhead â€” they route to the payroll path Â§2.7** (resolves #1, #4).

### 2.6 Report exports: GL / P&L Detail / Transaction Detail by Account

Lossy (no split detail, sign display-formatted) â†’ ingested primarily as **reconciliation control totals**, and as cost facts only when IIF is unavailable (and then marked provisional, Â§5). Row-type classifier runs first, keyed off: is col-1 populated while money cols empty (band header)? does the label start with `Total`/`Net`/`Gross` or equal `Beginning Balance`? does it match `Total <Parent> - Other` / `Total <Parent>` where children exist (roll-up)? are all money cells empty (structural)?

| Report row/column | Disposition | Handling |
|---|---|---|
| Title block (3-5 rows) | CTX | â†’ `SourceArtifact.report_meta_json`, and **`basis` + `date_locale` promoted to first-class dimensions** (resolves #26, #27) |
| Band-header row | CTX | sets current-account context; not a transaction |
| `Beginning Balance` row | CTX | GL only; opening context, never a cost |
| Transaction rows on `COGS`/`EXP`/`EXEXP` bands | MAP | the cost fact. **Signed amount rule stated explicitly: for a debit-normal account `signed = Debit âˆ’ Credit`; for a credit-normal account `signed = Credit âˆ’ Debit`, keyed to `LedgerAccount.normal_balance`. Single-`Amount`-column reports: strip `$`/commas, convert `(x)`/`x-`/red to sign** (hazards #9,10). Split `10100 Â· Checking` on U+00B7 (hazard #17). `Split = -SPLIT-` â†’ `needs_review` (offset unknown, hazard #12) |
| Running **`Balance`** column | CTX / reconciliation | **explicitly marked CTX; an assert guarantees the `Balance` column is never the money column feeding facts** (resolves #22) |
| `Total <account>` (leaf) | CTX (control) | leaf tie-out target (Â§6); never summed into facts (hazard #7) |
| **`Total <Parent> including subaccounts` roll-up** | CTX (control, non-summed) | classified `subtotal_parent_rollup`; **excluded from every fact sum and from every control-total sum; tie-out compares imported-per-leaf only to the leaf `Total <account>`, never the roll-up** (resolves #5) |
| Section totals: `Total COGS`, `Total Income`, `Gross Profit`, `Total Expenses`, `Total Other Income`, `Total Other Expense`, `Net Ordinary Income`, `Net Income` | CTX (control) | **all captured** so the closing identity can be asserted (Â§6 step 5b); never summed into facts (resolves #10) |
| `Name`, `Memo`, `Clr`, `Num`, `Adj` | CTX | dimensions/metadata |
| Transaction rows on `INC`/`EXINC`/`AR` bands | QUAR | `excluded_by_type = revenue_owned_by_freshbooks` (Â§3) |

### 2.7 Payroll Summary (pivot) + IIF `PAYCHECK` + `!EMP` â€” labor (single elected source)

Payroll Summary is a matrix: employees are columns, payroll items are rows, `TOTAL` column at right (hazard #23). Parse the **row label** as the field, each cell as `(employee-column Ã— item-row)`. **Payroll is the single authoritative labor source; Tier 1 loads no labor/payroll-typed account into `ExpenseItem`** (resolves #1, #4).

**`!EMP` mapping (new; prior draft had none):**

| `!EMP` column | Disposition | Target |
|---|---|---|
| `NAME`, `FIRSTNAME`, `LASTNAME`, `MIDINIT` | MAP | `Employee.name` |
| `SSNO` | MAP (sensitive) | `Employee.ssn` â€” **encrypted-at-rest + hash for round-trip; never surfaced in query/review UI in plaintext** (resolves #19) |
| `ADDR1..5`, `PHONE1/2`, `EMAIL` | CTX | contact block |
| `HIREDATE`, `RELEASEDATE`, `EMPTYPE` | CTX | employment metadata |
| `SALUTATION`, `NOTEPAD`, `CUSTFLD*` | CTX | preserved verbatim |

**Payroll Summary items:**

| Payroll item (row) | Disposition | Target |
|---|---|---|
| Gross Pay rows (Hourly/Salary/Bonus) â€” **component rows only** | MAP | field-tech gross â†’ informs `LaborSettings.tech_hourly_wage` (gross Ã· hours); admin gross â†’ `Employee`/`PayrollRun` flagged `admin` (feeds overhead **once**, via the payroll path, not via Tier 1 accounts). Field-vs-admin split by employee role (target Â§A.2) |
| Employer taxes (SS Company, Medicare Company, FUTA, SUTA), Total Employer Taxes | MAP | â†’ `LaborSettings.payroll_tax_burden_pct`. True labor cost = gross + employer taxes (semantics Â§5) |
| Employer benefit contributions | MAP | â†’ `LaborSettings.benefits_burden_pct` |
| Hours (Qty) on wage rows | MAP | â†’ `billable_hours_per_tech_per_year` sanity check; headcount â†’ `number_of_route_techs` |
| **`Total Gross Pay`, `Adjusted Gross Pay`, `Total Taxes Withheld`, any pivot subtotal, and the `TOTAL` column** | **CTX (control only)** | classified `payroll_subtotal`; **never summed with component rows.** `Adjusted Gross Pay` (gross minus pre-tax deductions) is treated as a **derived reconciliation check, not an additive earnings row** (resolves #20) |
| Taxes Withheld, Deductions from Net Pay, Net Pay | QUAR/CTX | `excluded_by_type` â€” withholdings are already inside gross; net pay credits Bank. Never added to cost (semantics Â§5, must-exclude #8) |

Detailed per-employee data â†’ `Employee`/`PayrollRun` (target gap B.4); a `wage` field is added to `TechnicianAssignment` (`ops_tables.py:62`, currently name + minutes only) for per-tech costing.

### 2.8 Coverage guarantee (corrected claim)

The prior draft's blanket claim ("every column named in the schema report has a row above") was inaccurate and is **retracted**. The corrected guarantee has two parts (resolves #18):

1. **Enumerated columns:** every column named in the schema report Â§1-8 now has an explicit `MAP`/`CTX`/`QUAR` row above, including the previously-omitted `!VEND SALUTATION/FIRSTNAME/MIDINIT/LASTNAME/NOTE`, `!INVITEM TAXABLE/SALESTAXCODE/DEP_TYPE/CUSTFLD1..5/HIDDEN/DELCOUNT`, `!CUST SADDR*`, and the full `!EMP` record. Two of these are load-bearing and now specified: `FIRSTNAME/LASTNAME` as vendor-resolution fallback when `COMPANYNAME` is blank; `HIDDEN=Y` masters excluded from auto-match.
2. **Unenumerated columns (version-specific / custom):** fall through to a **default `CTX` capture on the raw cell**, so an unrecognized column is preserved verbatim in `RawSourceCell`, never dropped. Byte-loss is impossible; the coverage claim is now scoped honestly to "no byte dropped," not "every column semantically mapped."

---

## 3. GATING / CONFIDENCE / WHITELIST

Every interpreted row lands in exactly one terminal `status`. Statuses group into gates. **Only `ready` rows are apply-eligible, and even those pass a human approval gate on first import of each account AND first sight of each external entity (Â§3.6).**

### 3.1 The status + reason set (extends `NormalizedSourceRecord`, `connector_tables.py:54-56`)

The existing `match_status`/`approval_status`/`apply_status` default to `'pending'` but nothing sets a terminal value (audit Â§3). Add these terminal statuses and reason codes â€” all **persisted and queryable**:

| Gate | Status | Reason codes |
|---|---|---|
| **APPLY-ELIGIBLE** | `ready` | (cost-base, resolved, sign clean, not money-movement) |
| **REVIEW** | `needs_review` | `split_offset_unknown` (-SPLIT-), `red_only_negative`, `vendor_suggested` (0.60â€“0.90), `reclass_journal`, `possible_depreciation_je`, `uncategorized_account`, `inventory_timing_unclear`, `unit_cost_no_qnty` (#6), `ambiguous_date_locale` (#27), `ambiguous_hierarchy` (#30), `first_sight_entity` (#12), `band_net_negative` (#29) |
| **EXCLUDED** | `excluded_by_type` | `revenue_owned_by_freshbooks`, `revenue_side_receivable`, `liability_expense_already_on_bill_split`, `funding_side_not_cost`, `capex_ingest_depreciation_instead`, `asset_movement_cost_flows_at_consumption`, `liability_movement_only_interest_is_cost`, `owner_draw_or_capital_not_cost`, `non_cost_item_type` (#21), `voided_or_zero` (#28) |
| **EXCLUDED** | `excluded_money_movement` | transfer / bill-payment / CC-payment / payroll-liability check |
| **QUARANTINE** | `quarantined_unmapped` | account/vendor/item not in ingested masters |
| **QUARANTINE** | `quarantined_parse` | `iif_block_unbalanced` (#13), `iif_orphan_split` / `iif_unterminated_block` / `iif_field_count_mismatch` (#14), `interpret_exception` + traceback (#15), `cell_count_mismatch` (#7), `red_only_ambiguous` |
| **ARTIFACT-LEVEL** | `quarantined_artifact` | `encoding_failure` (#8), `mixed_basis` (#26) |
| **SUPERSEDED** | `superseded` | `superseded_by_iif` (#2, #17), `superseded_by_payroll` (#4) â€” the row is kept, reason-coded, and excluded from aggregation |

Excluded, quarantined, and superseded are **not deletions**; they are visible, reason-coded, reversible. This closes the audit's biggest gap for the guarantee, and gives every failure case a terminal home (resolves #13, #14, #15).

### 3.2 The TYPE whitelist (auto-exclude, with the specific reason)

From semantics Â§1/Â§7. Account type drives an auto-exclusion a human can override but that never auto-applies:

| Account type / condition | Status | Reason code |
|---|---|---|
| `INC`, `EXINC` | `excluded_by_type` | `revenue_owned_by_freshbooks` |
| `AR` | `excluded_by_type` | `revenue_side_receivable` |
| `AP` | `excluded_by_type` | `liability_expense_already_on_bill_split` |
| `BANK`, `CCARD` | `excluded_by_type` | `funding_side_not_cost` |
| `FIXASSET` (purchase) | `excluded_by_type` | `capex_ingest_depreciation_instead` |
| `OCASSET`, `OASSET` | `excluded_by_type` | `asset_movement_cost_flows_at_consumption` |
| `OCLIAB`, `LTLIAB` | `excluded_by_type` | `liability_movement_only_interest_is_cost` |
| `EQUITY` | `excluded_by_type` | `owner_draw_or_capital_not_cost` |
| `AMOUNT==0` / `VOID:` memo | `excluded_by_type` | `voided_or_zero` (#28) |
| `INVITEMTYPE âˆˆ {DISC,SUBT,GROUP,PMT,STAX}` | `excluded_by_type` | `non_cost_item_type` (#21) |
| `COGS`, `EXP`, `EXEXP` | proceed to Â§3.3 | (the only cost base) |

`EXEXP` cost lines are tagged `non_operating` so interest/depreciation does not distort route/service margin (semantics Â§1). **Labor/payroll-typed `EXP`/`COGS` accounts (`is_labor_account`) are routed to the payroll path, not the overhead spine** (resolves #1, #4).

### 3.3 Confidence â†’ gate, for cost-base rows

Reuse existing confidence banding (`invoice_ingestion.py:92-98`: `high â‰¥ 0.95`, `assisted â‰¥ 0.75`, else exception) and customer-match thresholds (`STRONG 0.90`, `SUGGEST 0.60`, `customer_matching.py:32-33`):

- **`ready`**: account type âˆˆ {COGS, EXP, EXEXP}, not `is_labor_account`, `TRNSTYPE` not money-movement, not voided/zero, vendor/customer resolved â‰¥ 0.90 **and not a first-sight entity**, sign unambiguous, account exists in masters, date unambiguous under elected locale.
- **`needs_review`**: any reason code in Â§3.1's review list â€” including `-SPLIT-`, red-only negative, 0.60â€“0.90 vendor match, reclass JE, possible depreciation JE, `Uncategorized Expense`/`Ask My Accountant`, inventory timing, `unit_cost_no_qnty`, ambiguous date, ambiguous hierarchy, first-sight entity, net-negative cost band.
- **`quarantined_unmapped`**: account, vendor, or item not in ingested masters (import COA/vendors/items first, Â§5 Tier 0/2).

### 3.4 The no-double-count guard set (structural, I5)

1. **Revenue type hard-block:** any row with `INC`/`EXINC`, or account `AR`, is blocked with `revenue_owned_by_freshbooks`. Revenue never enters the cost store â†’ revenue double-count is structurally impossible (semantics Â§8).
2. **Source-of-truth election per `(account, period, basis)`:** cost has exactly one elected source per cell. Precedence: **IIF line detail > report totals**; **payroll detail > any payroll account total**. When a higher-precedence source arrives for a cell already carrying a lower one, the lower fact is marked `superseded` (`superseded_by_iif` / `superseded_by_payroll`) and **excluded from aggregation** â€” never summed. A reconciliation assert proves `Î£(non-superseded ExpenseActual) + Î£(BillLine) + Î£(PayrollRun)` has **no overlapping `(account, period, basis)`** (resolves #2, #4, #17).
3. **Labor lives in exactly one place:** `is_labor_account` accounts never write `ExpenseItem`/`ExpenseActual` overhead; labor is only `LaborSettings`/`PayrollRun`. A validation asserts **no `ExpenseItem` overhead row and no `LaborSettings` wage derive from the same QB account** (resolves #1, #4). This matters because `expenses.py:14-15` `annual_overhead_total` sums **every** `ExpenseItem.annual_cost` with no category filter and `cost_of_business.py:101` computes `true_cost = burdened_wage + overhead_per_hour` â€” so any labor left in `ExpenseItem` would be counted twice.
4. **Depreciation reconciles, never re-adds:** Tier 5 ingests depreciation JEs for asset attribution/dimensioning only; a validation asserts `Î£(Tier 5 depreciation) == the depreciation EXP/EXEXP account total already loaded` (`is_depreciation_account`). No new cost is created (resolves #3).
5. **Parent roll-ups never sum:** `subtotal_parent_rollup` rows are excluded from every fact and control-total sum; tie-out uses leaf totals only (resolves #5).
6. **GL-vs-item election:** the GL account line is the fact; the item is a descriptive tag. Item totals are never summed alongside GL (semantics Â§2, must-exclude #15).
7. **Payroll pivot subtotals never sum:** `payroll_subtotal` rows and the `TOTAL` column are control-only; `Adjusted Gross Pay` is a derived check (resolves #20).

Cost (QuickBooks) and revenue (FreshBooks) join only on `Customer` (and `Class` â†” service line), where the semantics report says profitability is built.

### 3.5 Review queue + backlog visibility (new, required)

`needs_review` / `quarantined_*` / `superseded` rows surface in a Streamlit review page (new; Â§4) modeled on the existing invoice review (`ui/pages/7_Invoice_Review.py`, `approve_staged_line`/`reject_staged_line`, `invoice_ingestion.py:130`). Approve writes `MatchCandidate` + `ApprovalDecision` + `ApplyEvent` + `ExternalIdentityMap` following `approve_communication` (`front_desk.py:1414-1441`). Nothing is auto-applied, nothing is dropped to clear the queue.

**Backlog is made loud (resolves #11):** the review dashboard shows, **per status, the DOLLAR value and % of total classified cost sitting un-applied**. The owner sign-off gate (Â§6 step 10) displays `"cost-per-hour excludes $X (Y%) still in review"` and **refuses to mark a tier `live` while un-applied classified cost exceeds a configured threshold** â€” so a review backlog can never silently deflate `true_cost_per_hour` (the skimmer failure reincarnated at the aggregate).

### 3.6 First-sight entity confirmation + auto-match sampling (new)

A wrong-but-confident match misattributes cost to the wrong entity â€” a semantic loss the byte round-trip cannot see. Therefore (resolves #12):

- **First-sight confirmation:** the **first** time a given external entity resolves (i.e. a new `ExternalIdentityMap` would be minted), the row is `needs_review` (reason `first_sight_entity`) and surfaced for one-time human confirmation **even at â‰¥0.90**. After the identity is confirmed and mapped, subsequent rows for that entity auto-apply.
- **Auto-match sampling:** each import surfaces a random sample of N already-mapped auto-matches for owner spot-check, so drift in the matcher is caught.

---

## 4. GAP ANALYSIS â€” BUILD FIRST

Everything below must exist **before** the first QuickBooks apply, or the no-loss/no-double-count guarantee cannot hold. Each cites the audit/target/critic finding requiring it.

### 4.1 Framework (the reusable skeleton)

1. **`BaseTranslator` abstraction + connector registry.** `app/connectors/__init__.py` is an empty namespace stub â€” no base class, no registry, drivers hand-wired. Build a `BaseTranslator` contract with four pluggable stages:
   - `tokenize(bytes) â†’ RawSourceRow[]` (file â†’ verbatim rows/cells, with byte offsets)
   - `classify(RawSourceRow) â†’ classification`
   - `interpret(RawSourceRow) â†’ NormalizedSourceRecord + semantic verdict`
   - `apply(NormalizedSourceRecord) â†’ ApplyEvent` (gated)

   **`classify()` and `interpret()` each run inside a per-row try/except** that writes `quarantined_parse` + traceback + reason `interpret_exception` and continues; a per-artifact post-condition asserts **interpretation-record count == RawSourceRow count** (resolves #15). A `TranslatorRegistry` maps `source_slug` + `artifact_type` â†’ translator. QuickBooks registers `iif`, `report_gl`, `report_pnl_detail`, etc.

2. **Generic ingest route.** `app/api/routes/connectors.py` exposes only RingCentral endpoints. Add `POST /connectors/{source}/artifacts` (upload) and `GET /connectors/{source}/review-queue`, register `quickbooks` via `ensure_source_system` (`ingestion.py:37`) and add it to `DEFAULT_SOURCE_SYSTEMS` (`bootstrap.py:38`).

### 4.2 No-loss substrate

3. **`SourceArtifact` + `RawSourceRow` + `RawSourceCell`** (Â§1.2) with **byte offsets**, `basis`, `date_locale`, and **sensitive-field encryption** (`is_sensitive`/`cipher_value`/`value_hash`). The existing raw layer is dict-grain (`RawSourceRecord`) or PDF-line-grain (`InvoiceLineStaging`); neither addresses byte-addressed fileâ†’rowâ†’cell for banded QB exports or PII-at-rest (resolves #8, #19).

### 4.3 Quarantine + review (the enforcement piece)

4. **Terminal quarantine/exclusion/superseded statuses + reason codes** on `NormalizedSourceRecord` (or a QB-specific interpretation table) per Â§3.1. Today nothing sets a terminal non-pending state (audit Â§3).
5. **Review-queue endpoint + Streamlit page** (new `ui/pages/2x_QuickBooks_Review.py`) modeled on `7_Invoice_Review.py`, **including the per-status dollar/% backlog panel** (Â§3.5) and the **first-sight-entity confirmation flow** (Â§3.6).

### 4.4 New target models (so QB data has a home; from target report Â§B)

6. **`Vendor` + `VendorProfile` + `VendorMatch`** and `resolve_vendor` (or generalize `customer_matching.resolve_customer` into `resolve_entity(profile_model, match_model, account_model)`), `ExternalIdentityMap` `entity_type='vendor'`, with `person_name` fallback and encrypted `tax_id`. Add FKs from `ProductPriceHistory`, `AssetRecord`, `CommercialVendorOrder`, `ExpenseItem` (audit Q4; target B.1; resolves #18, #19).
7. **`LedgerAccount`** (chart of accounts): `name`, `account_code`, `account_type`, parent link, **`normal_balance`, `is_labor_account`, `is_depreciation_account`, `account_role`**. Required so type + normal-balance + labor/depreciation classification stamp onto every transaction line (I3; target B.6; resolves #1, #3, #4, #29).
8. **`Bill` + `BillLine`** (A/P), mirroring `BillingDocument`/`BillingLine` (`ops_tables.py:9-27`) and populating `raw_json` this time (target B.2). **`BillLine` carries `provenance` (`iif_authoritative`) and `is_superseded`/`superseded_reason`** for the election mechanic.
9. **`ExpenseActual`** (period grain) + `account_code` on `ExpenseItem`. Today `ExpenseItem.annual_cost` is a single hand-seeded scalar (`bootstrap.py:12`); QB monthly-P&L-by-account cannot land at period grain (target B.3). **`ExpenseActual` carries `provenance` (`report_provisional` | `iif_authoritative`), `basis`, `is_superseded`/`superseded_reason`** so report facts can be superseded by IIF facts per `(account, period, basis)` (resolves #2, #17).
10. **`Employee` + `PayrollRun`** and a `wage` field on `TechnicianAssignment` (`ops_tables.py:62`); `!EMP` mapping with encrypted `ssn` (target B.4; resolves #19).
11. **`CompanyAsset`/`Vehicle`** + depreciation, distinct from the customer-property-bound `AssetRecord` (`asset_tables.py`) (target B.5). Optional later: GL/balance-sheet parity (B.6), inventory valuation/COGS-account fields (B.8), sales/use tax (B.9).
12. **`CostSourceElection`** (new, cross-cutting): keyed `(account_id, period, basis)`, records the elected authoritative source and drives the supersede sweep. The cost-of-business aggregation reads **at most one non-superseded source per cell** (resolves #2, #4, #17, I5).

### 4.5 Gated apply + reconciliation + integrity

13. **Approval-gated QB apply** following `approve_communication` (`front_desk.py:1414`), emitting `MatchCandidate`/`ApprovalDecision`/`ApplyEvent`/`ExternalIdentityMap`. **Do not** reuse the `freshbooks_revenue.py` ungated direct-write (audit Â§5).
14. **Reconciliation harness** at account/period grain with **`Decimal` money and explicit tolerance** (Â§6). `ReconciliationFact` (`ops_tables.py:39`) exists but is property-scoped; add a sibling `AccountPeriodReconciliation` for account/period/basis control-total tie-out, cross-foot, closing-identity, and exclusion-audit checks (resolves #7, #9, #10).
15. **Sensitive-field vault** (encryption-at-rest + hashed round-trip) for `SSNO`/`TAXID` (resolves #19).
16. **Composite natural-key identity** service (Â§1.3) feeding `ExternalIdentityMap` (resolves #23, #24).
17. **Scheduled byte-integrity sweep** re-hashing `SourceArtifact.file_path` vs `file_sha256` (resolves #25).

---

## 5. TIERED INGESTION PLAN

Each tier is independently valuable, independently validated, and gated behind owner acceptance before the next begins. Cost dollars never apply until the tier's validation (Â§6) passes. **Every tier's facts carry `provenance` and `basis`; the `(account, period, basis)` election (Â§3.4 guard 2) governs which fact counts.**

### Tier 0 â€” Framework + no-loss substrate + Chart of Accounts

- **Ingest:** IIF `!ACCNT` (or Account Listing report). Build Â§4.1-4.3 substrate, plus `LedgerAccount.normal_balance` / `is_labor_account` / `is_depreciation_account` (owner-confirmed classification of which accounts are labor/depreciation).
- **Unlocks:** the `account_type` + normal-balance + labor/depreciation dictionary every later tier reads; the verbatim spine; the review queue. No cost applied yet.
- **Risk:** low (schema build); the one judgement call is labor/depreciation account tagging â€” owner confirms.
- **Depends:** nothing.
- **Validation:** every account row round-trips (Â§6 step 2); every account has a type and a normal-balance; sub-account hierarchy reconstructed with no phantom parents (any colon-ambiguity is in review, not auto-created).

### Tier 1 â€” P&L overhead (NON-LABOR) â†’ cost-per-hour (highest leverage)

- **Ingest:** P&L Detail (or GL) **`EXP`/`EXEXP` accounts that are NOT `is_labor_account`** trailing-12-month totals â†’ `ExpenseItem.annual_cost` + `ExpenseActual` (period grain), `provenance=report_provisional`. **Labor/payroll accounts are explicitly EXCLUDED here and deferred to Tier 4; depreciation accounts are loaded here as the single depreciation source (Tier 5 only reconciles/dimensions)** (resolves #1, #3, #4).
- **Unlocks:** un-zeros `overhead_per_hour`, `true_cost_per_hour`, `break_even_bill_rate` (`cost_of_business.py:96-109`), currently 12 hand-seeded guesses including `office_rent = 0.0` (`bootstrap.py:22`). Highest-leverage fill (target Â§A.1).
- **Sign-off is explicitly provisional:** the Tier 1 sign-off is labelled **"overhead-only, provisional â€” direct cost (COGS) pending Tier 2-4, report-derived pending IIF supersede"**, so the owner is not accepting a structurally-incomplete number as final. COGS is excluded here by design (arrives Tiers 2-4); if the shop books direct cost in `EXP` rather than `COGS`, the name-keyword classifier flags those for owner routing (resolves #16, #17).
- **Risk:** COGS-vs-EXP classification (fall back to name-keyword classifier for shops with no COGS accounts, semantics Â§8); owner-draw false positives (guarded by EQUITY exclusion, Â§3.2).
- **Depends:** Tier 0.
- **Validation:** sum of imported non-superseded `ExpenseActual` per account == that account's leaf `Total <account>` subtotal (never the parent roll-up); grand total == QB `Total Expenses` minus labor accounts; **closing identity holds** (Â§6 step 5b). Recompute cost-per-hour, show beside the old seeded number, with the "excludes $X in review" banner, for owner sign-off (Â§6 step 10).

### Tier 2 â€” Vendors + item/material unit costs

- **Ingest:** `!VEND`/Vendor Contact List â†’ `Vendor`; Item Listing (with Cost)/`!INVITEM` â†’ `ChemicalProduct.default_unit_cost` + `default_vendor`.
- **Unlocks:** chemical cost stops silently reading 0. Today, with no price history, unit cost falls to `0.0` (`profitability.py:104`, `variance.py:217`).
- **Risk:** vendor match ambiguity (0.60-0.90 â†’ `needs_review`; first-sight â†’ confirm Â§3.6); item-vs-GL double count (guard Â§3.4); `%`-valued and non-cost item types excluded (Â§2.4, resolves #21); `HIDDEN=Y` masters excluded from auto-match (resolves #18).
- **Depends:** Tier 0; Vendor spine (Â§4.4).
- **Validation:** every vendor and item resolves, quarantines, or is excluded with a reason; imported `default_unit_cost` values eyeballed against Item Listing `Cost`; no negative/inf unit cost exists (resolves #6).

### Tier 3 â€” Bill / GL line-level cost with dimensions (IIF authoritative â†’ supersede Tier 1)

- **Ingest:** `!TRNS`/`!SPL` (IIF preferred) `BILL`/`CHECK`/`CCARD` â†’ `Bill`/`BillLine` (`provenance=iif_authoritative`) + dated `ProductPriceHistory.unit_cost` (`create_price_history`, `expenses.py:32`), carrying `Class` and `Customer:Job`.
- **Supersede path (new, mandatory):** for every `(account, period, basis)` where Tier 3 IIF detail exists, **the Tier 1 `ExpenseActual` row for that cell is marked `superseded` (`superseded_by_iif`) and excluded from aggregation** â€” never summed. `CostSourceElection` records the switch (resolves #2, #17).
- **Unlocks:** per-vendor dated unit costs (feeds `latest_unit_cost`, `expenses.py:23`), job-costed COGS, real variance actuals, route P&L cost side (`route_pnl.py`).
- **Risk:** split sign handling; **double count with Tier 1** â€” eliminated by the supersede election above; inventory-asset vs COGS timing (perpetual â†’ COGS at consumption, must-exclude #13); unbalanced/malformed blocks â†’ quarantine (resolves #13, #14).
- **Depends:** Tier 2; `Bill`/`BillLine` + `CostSourceElection` (Â§4.4).
- **Validation:** per-block exact-zero `TRNS.AMOUNT + Î£SPL.AMOUNT == 0` (unbalanced â†’ quarantine block); sum of applied cost-account splits for a period == independent GL/P&L account total for those accounts **within tolerance**; assert **no overlapping non-superseded `(account, period, basis)`** across `ExpenseActual` and `BillLine` (resolves #2, #9, #13).

### Tier 4 â€” Payroll detail (single authoritative labor source)

- **Ingest:** Payroll Summary pivot + `PAYCHECK` IIF + `!EMP` â†’ `Employee`/`PayrollRun`; field labor â†’ `LaborSettings` wage/burden; admin labor â†’ `Employee`/`PayrollRun` flagged `admin` feeding overhead **once via the payroll path** (never via Tier 1 accounts, which excluded all labor).
- **Unlocks:** replaces the 5-field `LaborSettings` guesses (`bootstrap.py:47`) with actual burdened labor rate; per-tech cost via `TechnicianAssignment.wage`.
- **No double count (resolves #1, #4):** because Tier 1 loaded **no** labor/payroll account, and payroll is the elected authoritative labor source, labor appears exactly once. Validation asserts no `ExpenseItem`/`LaborSettings` value derives from the same QB account.
- **Risk:** pivot parsing (hazard #23); pivot subtotal/`TOTAL`/`Adjusted Gross Pay` double count â†’ excluded as control-only (resolves #20); withholding double count â†’ excluded (Â§2.7); field-vs-admin split (target Â§A.2); SSN PII â†’ encrypted (resolves #19).
- **Depends:** Tier 0 (labor account tags), Tier 1 (admin overhead context).
- **Validation:** gross + employer taxes reconcile to Payroll Summary `TOTAL` column within tolerance; withholdings confirmed excluded; components never summed with subtotals.

### Tier 5 â€” Fixed assets, depreciation reconciliation, balance-sheet parity (optional)

- **Ingest:** `FIXASSET` + depreciation JEs â†’ `CompanyAsset` + vehicle/equipment **attribution/dimensioning only**; optionally GL balance-sheet accounts for full parity.
- **Depreciation reconciles, never re-adds (resolves #3):** Tier 1 already loaded the depreciation `EXP`/`EXEXP` account as the single depreciation cost source. Tier 5 ingests the JE to attribute depreciation to specific assets/vehicles and **asserts `Î£(Tier 5 depreciation) == the depreciation account total already loaded`**. No new cost is created.
- **Risk:** CAPEX vs period cost (purchase excluded, must-exclude #11); loan principal exclusion (only interest is cost, must-exclude #10).
- **Depends:** Tier 3.
- **Validation:** depreciation ties to the depreciation account total (not additive); no fixed-asset purchase in cost facts.

---

## 6. VALIDATION AGAINST REAL DATA

Run this procedure the moment the owner's actual export files arrive. It proves I1-I5 hold against real data, not fixtures. **All money is `Decimal`; intra-file identities are exact-zero; cross-export tie-outs use an explicit tolerance `Â±$0.01 Ã— line_count`, and any breach routes the specific offending block/account to quarantine rather than halting the whole ingest** (resolves #9).

1. **Intake, untouched.** Store bytes verbatim under `UPLOAD_DIR`, compute `file_sha256`, `byte_size`, detect encoding + `basis` + `date_locale`. Never mutate the file. Record `artifact_type`. **On encoding failure (U+FFFD or non-round-tripping bytes), set `quarantined_artifact`/`encoding_failure` and stop before row creation** (resolves #8).

2. **Byte-anchored round-trip (proves no-loss at ingest).** Using each `RawSourceRow.byte_offset_start:byte_offset_end`, slice the **original file bytes** and compare to the stored record; and re-encode the reconstructed rows and compare **byte-for-byte against `file_sha256`**. Both sides are raw bytes, so a codec-level mojibake cannot pass. **Zero byte diff is the pass condition** for I1; any diff halts that artifact (resolves #8).

3. **Row/cell count reconciliation.** Physical record count == `RawSourceRow` count. **Every data row's cell count == the active header column width; a mismatch quarantines that row (`cell_count_mismatch`)** rather than silently merging/shifting (IIF hazard #26; resolves #7, #14).

4. **Cell-segmentation validation (proves meaning, not just bytes â€” resolves #7).**
   - (a) **Re-serialize** each row's `RawSourceCell`s with the detected delimiter/quoting and assert the result reconstructs `raw_line_text` exactly. A layout misdetection (Debit/Credit vs single Amount, wrong delimiter, shifted header) fails here.
   - (b) Assert cell count == active header width (from step 3) or quarantine.
   - (c) **Numeric cross-foot (hard gate, not owner-eyeball):** for each band, `Î£(parsed money column) == that band's captured leaf `Total` control row` within tolerance. A misparsed money column fails the gate.

5. **Control-total tie-out + closing identity (proves correct application).**
   - **(a) Per-account:** sum imported non-superseded `ExpenseActual`/`Bill` cost per account == the report's leaf `Total <account>` subtotal (never the `subtotal_parent_rollup`, resolves #5); grand total == `Total Expenses` (non-labor) within tolerance.
   - **(b) Closing identity (resolves #10):** capture every section control total and assert `Total Income âˆ’ Total COGS âˆ’ Total Expenses âˆ’ Total Other Expense + Total Other Income == Net Income` from the report, AND assert the **classified sum (cost buckets + excluded-revenue + excluded-capital/movement) reproduces the `Net Income` control row**. Every dollar on the statement lands in exactly one bucket and the buckets close to Net Income â€” a whole missed section (e.g. `Other Expense`, or omitted `COGS`) is caught here.
   - **(c) IIF:** every `TRNS`+`SPL` block satisfies exact-zero `TRNS.AMOUNT + Î£SPL.AMOUNT == 0` (unbalanced â†’ quarantine the block, `iif_block_unbalanced`, resolves #13); Î£ applied cost-account splits == independent GL/P&L total for those accounts within tolerance.
   - **(d) Sign sanity (resolves #29):** on each `COGS`/`EXP` band the net signed sum (per `signed = Debit âˆ’ Credit` for debit-normal accounts) must be **positive** (costs); a net-negative band flags `band_net_negative` to review rather than silently applying flipped signs.

6. **Election / no-double-count audit (proves I5).**
   - Assert **no overlapping non-superseded `(account, period, basis)`** across `ExpenseActual`, `BillLine`, `PayrollRun` (resolves #2, #4).
   - Assert **no `ExpenseItem` overhead row and no `LaborSettings` wage derive from the same QB account** (resolves #1, #4).
   - Assert **`Î£(Tier 5 depreciation) == depreciation-account total already loaded`** (resolves #3).
   - Assert **`subtotal_parent_rollup` rows and payroll pivot subtotals contributed to zero facts** (resolves #5, #20).
   - Assert **all artifacts feeding a single aggregation share one `basis`; refuse to reconcile/aggregate mixed basis for the same period** (`mixed_basis`, resolves #26).

7. **Exclusion audit (proves nothing lost, nothing wrong included).** Emit every `excluded_*`/`quarantined_*`/`superseded` row with reason code. Assert **Î£ excluded `INC`/`EXINC` == QB `Total Income`** within tolerance â€” proves we captured all revenue and correctly refused every dollar of it (I3 + double-count guard). Owner eyeballs the exclusion list to confirm no real cost was excluded.

8. **Quarantine + backlog review.** Every `needs_review`/`quarantined_*` row appears in the review queue; assert none was auto-applied. **The dashboard reports, per status, the dollar value and % of total classified cost un-applied** (resolves #11).

9. **Idempotency + re-parse (resolves #23, #24).** Re-import the identical file â†’ zero new facts (dedup by `file_sha256`). **Re-export the same period (restamped `!HDR`) â†’ zero new facts (dedup by composite natural key).** Re-parse (drop derived rows, rebuild from `RawSourceRow`) â†’ identical output; **re-parse is blocked while applies exist, and re-parse-after-rollback produces zero new applies.**

10. **Owner sign-off gate (the human checkpoint that enforces "understand before applying").** Recompute `compute_cost_of_business` (`cost_of_business.py:78`) and present `true_cost_per_hour` beside the pre-import seeded value, **with the banner "cost-per-hour excludes $X (Y%) still in review" and the tier's provenance label (e.g. Tier 1 = "overhead-only, provisional")**. The gate **refuses `live` while un-applied classified cost exceeds threshold** (resolves #11, #16). The tier is not live until the owner accepts the reconciled number.

11. **First-sight + sampling (resolves #12).** Assert every first-mint external entity passed one-time human confirmation before auto-apply; present the random auto-match sample for spot-check.

12. **PII posture (resolves #19).** Assert `SSNO`/`TAXID` are stored encrypted-at-rest (ciphertext + hash), never surfaced in plaintext in any query/review view, and still byte-round-trip.

13. **Byte-integrity sweep live (resolves #25).** Confirm the scheduled job re-hashes all `SourceArtifact.file_path` vs `file_sha256` and alarms on mismatch/missing.

---

## IMMEDIATE NEXT STEPS

**Build first (in this order):**

1. **No-loss substrate + framework** â€” `BaseTranslator`/`TranslatorRegistry` in `app/connectors/__init__.py` with per-row try/except and the interpretation-count post-condition; `SourceArtifact`/`RawSourceRow`/`RawSourceCell` **with byte offsets, `basis`, `date_locale`, and the sensitive-field vault**; generic ingest routes in `app/api/routes/connectors.py`; register `quickbooks` in `bootstrap.py:38`. (Â§4.1-4.3, Â§4.5.15-17)
2. **`LedgerAccount` with `normal_balance` / `is_labor_account` / `is_depreciation_account`** and the **`CostSourceElection` `(account, period, basis)` table** â€” these two are where the no-double-count mandate actually lives; nothing else can be safely applied until they exist. (Â§4.4.7, Â§4.4.12)
3. **Terminal status/reason set + review queue + backlog panel + first-sight confirmation** on `NormalizedSourceRecord` and `ui/pages/2x_QuickBooks_Review.py`. (Â§3.1, Â§3.5, Â§3.6, Â§4.3)
4. **Remaining target models** â€” `Vendor` (+ person-name fallback, encrypted `tax_id`), `Bill`/`BillLine` (+ provenance/supersede), `ExpenseActual` (+ provenance/basis/supersede), `Employee`/`PayrollRun` (+ encrypted `ssn`), `CompanyAsset`. (Â§4.4)
5. **Gated apply + reconciliation harness** (`Decimal`, tolerance, cross-foot, closing-identity, election audit) following `approve_communication` (`front_desk.py:1414`), never `freshbooks_revenue.py`. (Â§4.5)

**Validate against the owner's real export (highest-signal checks, run in this order the moment files arrive):**

- **Byte-anchored round-trip + cell cross-foot** on the real Chart of Accounts and one P&L â€” proves bytes AND meaning survive before any apply (Â§6 steps 2-5).
- **Closing-identity reconciliation** on the real P&L â€” proves no whole section (Other Expense / COGS) is missed (Â§6 step 5b).
- **Election audit** after loading Tier 1 (non-labor overhead) then Tier 3 (IIF) for one overlapping period â€” proves the supersede path eliminates the report-vs-IIF and labor double-counts, which are the confirmed breaks today (`cost_of_business.py:101`, `expenses.py:14-15`, `bootstrap.py:23-24`) (Â§6 step 6).
- **Owner sign-off on the provisional Tier 1 number** with the "excludes $X in review / overhead-only" banners visible â€” confirms the human gate refuses to accept a structurally-incomplete cost-per-hour as final (Â§6 step 10).

---

### Finding-coverage matrix (all 30 resolved)

| # | Where resolved |
|---|---|
| 1 labor double-count | Â§2.1 `is_labor_account`, Â§2.5, Â§3.2, Â§3.4-3, Tier 1/4, Â§6-6 |
| 2 report vs IIF double-count | Â§3.4-2, Â§4.4.12 `CostSourceElection`, Â§4.4.9 provenance, Tier 3 supersede, Â§6-6 |
| 3 depreciation double-count | Â§2.1 `is_depreciation_account`, Â§3.4-4, Tier 1/5, Â§6-6 |
| 4 admin/payroll double-count | Â§2.7, Â§3.2, Â§3.4-2/3, Tier 1/4, Â§6-6 |
| 5 parent roll-up | Â§1.2 `subtotal_parent_rollup`, Â§2.6, Â§3.4-5, Â§6-5a |
| 6 AMOUNT/QNTY guard | Â§2.5, Â§3.1/3.3 `unit_cost_no_qnty`, Tier 2 validation |
| 7 cell segmentation | Â§1.2, Â§6-3, Â§6-4 |
| 8 byte vs decode round-trip | Â§1.2 byte offsets + `encoding_failure`, Â§6-1/2 |
| 9 Decimal + tolerance | Â§2 intro, Â§6 intro, Â§6-5 |
| 10 closing identity | Â§2.6, Â§6-5b |
| 11 backlog deflation | Â§3.5, Â§6-8, Â§6-10 |
| 12 first-sight confirmation | Â§3.6, Â§6-11 |
| 13 unbalanced block | Â§2.5, Â§3.1 `iif_block_unbalanced`, Â§6-5c |
| 14 malformed block | Â§3.1 `iif_orphan_split`/`iif_unterminated_block`/`iif_field_count_mismatch`, Â§6-3 |
| 15 interpret exception | Â§4.1 try/except + count post-condition, Â§6 |
| 16 Tier 1 COGS-incomplete | Tier 1 provisional label, Â§6-10 |
| 17 apply-before-understood | Â§4.4.9 `report_provisional`, Tier 3 supersede, Â§3.4-2 |
| 18 unmapped columns | Â§2.2/2.3/2.4/2.8 enumerations, `HIDDEN` gate, person-name fallback |
| 19 !EMP / SSN PII | Â§1.2 sensitive vault, Â§2.2/2.7, Â§4.5.15, Â§6-12 |
| 20 payroll pivot subtotals | Â§2.7 `payroll_subtotal`, Â§3.4-7 |
| 21 non-cost item types / % | Â§2.4, Â§3.2 `non_cost_item_type` |
| 22 running Balance column | Â§2.6, assert |
| 23 sha256 vs re-export | Â§1.3 composite natural key, Â§6-9 |
| 24 re-parse orphans applies | Â§1.3 block/re-link + test, Â§6-9 |
| 25 byte-integrity sweep | Â§1.3, Â§4.5.17, Â§6-13 |
| 26 cash vs accrual | Â§1.2 `basis`, Â§2.6, Â§6-6 |
| 27 date-locale | Â§1.2 `date_locale`, Â§2.5, Â§3.1 `ambiguous_date_locale` |
| 28 voided/zero | Â§2.5, Â§3.2 `voided_or_zero` |
| 29 Debit/Credit sign | Â§2.1 `normal_balance`, Â§2.6, Â§6-5d |
| 30 colon-in-name | Â§2.1/2.3, Â§3.1 `ambiguous_hierarchy` |

**Design principle in one line:** store every byte of every QuickBooks file verbatim and byte-addressable forever; interpret each line by its account TYPE, normal-balance sign, and basis; refuse revenue, money-movement, capital, and voids for coded visible reasons; quarantine every uncertain or failed row into a review queue with a terminal status; elect exactly one authoritative source per `(account, period, basis)` so no dollar counts twice; and let nothing touch a cost target except through a gated, reversible, `Decimal`-reconciled apply whose tie-outs close to Net Income and whose un-applied backlog is shown to the owner before sign-off.