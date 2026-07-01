from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]  # ui/pages/00_Development.py -> repo root
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd
import streamlit as st
from sqlmodel import Session, select

from ui._shared import configure_page, page_header
from app.core.database import create_db_and_tables, engine
from app.models.dev_tracker import DevItem, DevLogEntry

configure_page('Development Tracker', icon='🧱')

# Current build stamp (bump when a new batch of work ships). Modeled on Lumen's
# DEV_VERSION: every changelog entry is tagged with the build it shipped in.
DEV_BUILD = '2026.06.30-h'

# --------------------------------------------------------------------------
# Vocabularies
# --------------------------------------------------------------------------
PRIORITY_OPTIONS = ['P0', 'P1', 'P2', 'P3', '-']
STATUS_BY_CATEGORY = {
    'feature': ['working', 'partial', 'stub'],
    'health': ['open', 'in_progress', 'resolved', 'wont_fix'],
    'idea': ['proposed', 'planned', 'in_progress', 'done', 'parked'],
}
DEFAULT_STATUS = {'feature': 'working', 'health': 'open', 'idea': 'proposed'}
PRIORITY_RANK = {'P0': 0, 'P1': 1, 'P2': 2, 'P3': 3, '-': 4}
FEATURE_STATUS_RANK = {'working': 0, 'partial': 1, 'stub': 2}

# Changelog entry kinds -> (emoji badge, label). Emoji gives at-a-glance scanning
# in Streamlit without fighting CSS, echoing Lumen's colored status chips.
KIND_META = {
    'shipped':  ('\U0001F680', 'Shipped'),    # rocket
    'fix':      ('\U0001F527', 'Fix'),         # wrench
    'refactor': ('♻️', 'Refactor'),  # recycle
    'cleanup':  ('\U0001F9F9', 'Cleanup'),     # broom
    'infra':    ('\U0001F3D7️', 'Infra'),  # construction
    'docs':     ('\U0001F4DD', 'Docs'),        # memo
}
KIND_OPTIONS = list(KIND_META.keys())

CATEGORY_META = {
    'feature': (
        'Working Features',
        'What the platform actually does today, with honest flags on partial and stub pieces.',
    ),
    'health': (
        'Code Health',
        'Architecture and code-quality findings from the full review, ranked by priority.',
    ),
    'idea': (
        'Ideas & Roadmap',
        'Improvements to build, grounded in the code review plus 2026 market and AI research. Add your own anytime.',
    ),
}

# --------------------------------------------------------------------------
# Seed content: the full review as of 2026-06-30 (4-agent code review + market research)
# Each tuple: (category, priority, area, status, title, detail, source)
# --------------------------------------------------------------------------
DEFAULT_DEV_ITEMS = [
    # ---- WORKING FEATURES ------------------------------------------------
    ('feature', '-', 'Estimation', 'working', 'Residential & commercial estimation engine',
     'Data-driven pricing: gallons x coefficient x condition-multiplier x calibration-factor, with versioned BaselineModelVersion coefficients in the DB, burdened labor, amortized overhead, and margin. The strongest part of the codebase.',
     'Code review: services'),
    ('feature', '-', 'Estimation', 'working', 'Heater & equipment sizing',
     'Real thermodynamic BTU math, candidate ranking into recommendation bands, and an equipment-package builder/wizard/selector with preview-then-commit. ~3,100 LOC of genuine logic.',
     'Code review: services'),
    ('feature', '-', 'Quoting', 'working', 'Quote workflow state machine',
     'Quote cases with enforced stage transitions (allowed_next), stage history, staleness/follow-up tracking, and dashboard rollups that mirror CRM bucket language. The 86KB workflow page is the UI centerpiece.',
     'Code review: services/API'),
    ('feature', '-', 'Connectors', 'working', 'FreshBooks integration',
     '3-legged OAuth (start/callback/refresh with CSRF state), draft-estimate push, reconcile, mark-sent, and signed inbound webhooks (HMAC-SHA256). Real API client, used live when configured.',
     'Code review: API/services'),
    ('feature', '-', 'Connectors', 'working', 'LACRM (Less Annoying CRM) integration',
     'Full urllib client: contacts, pipelines, pipeline items, tasks, notes, webhooks, with a signed webhook handshake. Live writes are gated behind dry-run default + a typed confirmation phrase.',
     'Code review: services'),
    ('feature', '-', 'Communications', 'working', 'Front-desk SMS/call triage',
     'Review queue, contact-match candidate scoring, operator decisions, and a gated LACRM apply (dry-run default; live needs confirm_live_write + typed phrase + idempotency key).',
     'Code review: services/API'),
    ('feature', '-', 'Communications', 'partial', 'RingCentral inbound ingestion',
     'Webhook -> normalized records works. But it is inbound-only: there is no RingCentral API client, so the platform cannot send SMS or place calls outbound yet.',
     'Code review: services'),
    ('feature', '-', 'Billing', 'working', 'Invoice ingestion',
     'PDF/TXT/CSV upload, pypdf text extraction, regex line parsing, fuzzy product/property matching, and price-history staging that feeds back into estimate costs.',
     'Code review: services/UI'),
    ('feature', '-', 'Operations', 'working', 'Commercial deliveries',
     'Monthly delivery and property-level billing review, CRUD, and pandas/openpyxl XLSX export.',
     'Code review: services'),
    ('feature', '-', 'Operations', 'working', 'Accounts / properties / vessels',
     'Core customer-asset management CRUD across Account, Property, and PoolVessel.',
     'Code review: UI'),
    ('feature', '-', 'Front Desk', 'working', 'Property verification / caller vetting',
     'Tools page: create/list property-authority verification cases, an approved-agents registry, and tool history. Clean form-based UI.',
     'Code review: UI'),
    ('feature', '-', 'Estimation', 'working', 'Estimate library',
     'Save/list/compare estimate runs, export HTML/JSON/PDF, and reload a saved estimate back into the estimator.',
     'Code review: UI'),
    ('feature', '-', 'Estimation', 'working', 'Compare & Train calibration',
     'Computes variance of estimate vs logged actual usage, suggests per-property multipliers, and persists CalibrationAdjustment that feeds back into pricing. The learning loop closes.',
     'Code review: services'),
    ('feature', '-', 'Admin', 'working', 'Admin cost editor',
     'Editable grids for expenses and chemical products with price history, written straight back to the DB.',
     'Code review: UI'),
    ('feature', '-', 'UI', 'working', 'Operations dashboard',
     'KPI metrics (accounts/properties/quotes/sync state), an operations launchpad, and LACRM + FreshBooks sync-readiness panels.',
     'Code review: UI'),
    ('feature', '-', 'Connectors', 'partial', 'Heritage catalog connector',
     'Working client with remote + local-file catalog fetch and robust normalization, but DEFAULT_HERITAGE_CATALOG_URL is empty, so it falls back to a hardcoded catalog unless env-configured.',
     'Code review: services'),
    ('feature', '-', 'Operations', 'working', 'Diagnostics pages',
     'Integration / environment / text-quality health dashboards that probe local services and export JSON snapshots.',
     'Code review: UI'),
    ('feature', '-', 'Connectors', 'partial', 'Skimmer ops connector',
     'Client (skimmer-api-key header) + normalizers + sync pipeline landing work orders as service visits with labor + chemical actuals, service locations as properties, bodies of water as vessels. Idempotent; chemicals matched to seeded products. Runs in fixture mode today (bundled sample data); set SKIMMER_API_KEY to go live. app/connectors/skimmer/* + app/services/skimmer_sync.py + ui/pages/21_Skimmer.py; 4 tests.',
     'Build 2026.06.30-g'),
    ('feature', '-', 'Cost Engine', 'working', 'True cost-of-doing-business ($/hour) engine',
     'Fully-loaded cost per billable hour: burdened wage (payroll tax + benefits) + every expense amortized across billable capacity. Workers-comp called out; break-even bill rate at a target margin; live what-if inputs that save back to labor settings. Composes the existing burdened_labor_rate + overhead_per_billable_hour; math locked by 4 tests. app/services/cost_of_business.py + ui/pages/18_Cost_of_Business.py.',
     'Build 2026.06.30-c'),
    ('feature', '-', 'Purchasing', 'working', 'Purchasing intelligence (best source + price anomalies)',
     'Supplier price book per product, cheapest-current-vendor recommendation with cross-vendor spread, and price-anomaly flags, computed over ProductPriceHistory (fed by invoice ingestion or manual entry). Manual price-observation entry on the page. app/services/purchasing.py + ui/pages/19_Purchasing.py; logic locked by 4 tests.',
     'Build 2026.06.30-e'),
    ('feature', '-', 'Identity', 'working', 'Customer identity matching (3-pass)',
     'Resolves Skimmer customers and FreshBooks clients into one account so cost and revenue join. Pass 1 exact email, pass 2 exact phone / strong fuzzy name (auto), pass 3 manual queue for ambiguous; new customers create a fresh account. Manual confirm/relink/unlink override, persisted. CustomerProfile + CustomerMatch tables; app/services/customer_matching.py + ui/pages/22_Customer_Matching.py; 5 tests.',
     'Build 2026.06.30-h'),
    ('feature', '-', 'Assets', 'working', 'Asset lifecycle registry',
     'Tracks physical assets through ordered -> received -> installed -> retired with serial/model numbers, purchase provenance, install location (property + vessel), and warranty. Per-property asset lists; installed-base value + expiring-warranty rollups. New AssetRecord table alongside the thin legacy EquipmentAsset. app/services/assets.py + ui/pages/20_Assets.py; lifecycle locked by 3 tests.',
     'Build 2026.06.30-f'),

    # ---- CODE HEALTH FINDINGS -------------------------------------------
    ('health', 'P0', 'Security', 'open', 'No authentication or authorization anywhere in the API',
     'Grep confirms zero Depends/Security/middleware/CORS across app/api. Every endpoint is public, including admin/bootstrap (re-seeds the DB) and the live-write sync + OAuth-refresh endpoints. Top risk for any deployment.',
     'Code review: API'),
    ('health', 'P0', 'Methodology', 'resolved', 'routing_bridge_* subsystem implements nothing',
     '~32 route+service files, ~4,444 LOC, 70-80% verbatim-duplicated boilerplate. Every file returns a JSON report attesting that it did nothing. The real safety gate exists once, correctly, in front_desk. RESOLVED 2026-06-30: all 32 files archived to archive/ and de-wired from app.py; nothing real was lost (verified: only planning attestations).',
     'Code review: services/API'),
    ('health', 'P0', 'Methodology', 'resolved', 'Phase-ladder ceremony dominates the repo',
     '~8,000 generated files; 2,035 of 2,060 commits are "Phase NN Step NN"; ~99% of test files only assert "file exists / string present"; 1,598 backup folders; ~993 installer scripts. RESOLVED 2026-06-30: ~8,135 ladder files archived to archive/ (pages/tests/scripts/docs); live tree audited to confirm no real code was swept. backups/ gitignored.',
     'Code review: methodology'),
    ('health', 'P0', 'UI', 'resolved', '~2,000 auto-generated packet pages pollute the sidebar',
     'ui/pages held ~2,046 files; only ~26 are real. The Phase packet pages do not even import app.* -- they print a static safety block. RESOLVED 2026-06-30: ui/pages reduced to 26 live feature pages; all bridge/Phase packet pages archived.',
     'Code review: UI'),
    ('health', 'P1', 'Data', 'open', 'SQLite not hardened for concurrency',
     'The engine sets check_same_thread=False but no WAL journal mode, no busy_timeout, no pool. Concurrent webhook writes will hit "database is locked". The most likely production failure mode.',
     'Code review: API'),
    ('health', 'P1', 'API', 'open', 'No dependency injection for DB sessions',
     'get_session() exists but no route uses it; there are ~200 hand-rolled "with Session(engine)" blocks. Blocks request-scoped transactions, test overrides, and transaction middleware.',
     'Code review: API'),
    ('health', 'P1', 'Data Model', 'open', 'No foreign keys, no enums, mixed datetimes',
     'Every relationship is a bare indexed int (no FK, no referential integrity, every join is a manual second query). Status fields are free-text strings (a typo creates an invalid state). Naive utcnow in models vs aware now(UTC) in newer code.',
     'Code review: API'),
    ('health', 'P1', 'Security', 'open', 'Secrets stored in plaintext',
     'FreshBooks OAuth access/refresh tokens are written unencrypted to data/freshbooks_oauth_tokens.json; webhook secrets are persisted as plaintext SystemSetting rows.',
     'Code review: API'),
    ('health', 'P1', 'Services', 'open', 'Per-row commits inside loops',
     'Services commit after each row inside batch loops (front_desk apply, commercial). A partial failure leaves a half-written batch with no surrounding transaction or rollback.',
     'Code review: services'),
    ('health', 'P1', 'Security', 'open', 'RingCentral webhook is unauthenticated',
     'push_ringcentral_event accepts any payload with no signature/secret check, unlike the signed FreshBooks/LACRM webhooks. An open ingestion endpoint.',
     'Code review: API'),
    ('health', 'P1', 'Testing', 'open', 'Test signal-to-noise ~1.3%; no CI',
     '~2,028 of ~2,053 tests only check file existence / marker strings. The ~26 real behavioral tests that exist are good (heater math, live-write-blocked), but no CI runs them, so thousands of meaningless green checks hide whether the real ones pass.',
     'Code review: methodology'),
    ('health', 'P1', 'Maintainability', 'open', 'front_desk.py is a 1,514-line god module',
     'Mixes mojibake repair, SMS review, candidate scoring, LACRM apply gating, and audit export. Should split into sms_review / contact_matching / lacrm_apply / text_quality.',
     'Code review: services'),
    ('health', 'P2', 'Maintainability', 'open', 'Business data hardcoded in source',
     '~1,000 lines of literal pricing/catalog dicts in heater_quote.py plus magic seed coefficients in bootstrap.py. Adding a chemical requires editing two dicts (alias_map coupling). Belongs in DB/config, where the infra already exists.',
     'Code review: services'),
    ('health', 'P2', 'UI', 'open', 'No error handling around UI DB writes',
     'The DB-direct pages (admin costs, estimators, even the 86KB quote workflow) have no try/except around commits; a bad cast surfaces as a raw Streamlit traceback.',
     'Code review: UI'),
    ('health', 'P2', 'UI', 'in_progress', 'No shared UI helper module',
     'sys.path bootstrap + Session(engine) + bridge-probe code are copy-pasted into every page. IN PROGRESS 2026.06.30-d: ui/_shared.py created (configure_page, page_header, section, db_session) and applied to Dashboard, Development, and Cost of Business. Remaining pages still need migration.',
     'Code review: UI'),
    ('health', 'P2', 'API', 'open', 'Untyped dict request bodies',
     'tools.py and connectors.py accept "payload: dict" with no Pydantic schema, bypassing validation. reports.py parses dates with no try/except, so bad input is an unhandled 500.',
     'Code review: API'),
    ('health', 'P2', 'Performance', 'open', 'Counts load all rows into memory',
     'connectors.py counts via len(list(session.exec(select(model)).all())) and pulls all raw+normalized rows just to bucket them. Will not scale.',
     'Code review: API'),
    ('health', 'P2', 'Cleanup', 'open', 'Misleading lazy imports & dead code',
     '"from datetime import timedelta" placed after the function that uses it (lacrm_sync, freshbooks_sync); discarded query results in front_desk; estimator.py service file misplaced inside ui/pages.',
     'Code review: services/UI'),
    ('health', 'P2', 'Safety', 'open', '"Safety" is inert marker strings, not controls',
     'planning_only=true and friends are literals that tests only check for presence; they gate nothing at runtime. Real safety is the separate confirm_live_write mechanism. Replace marker tests with tests against the real guard.',
     'Code review: methodology'),
    ('health', 'P3', 'UI', 'in_progress', 'Inconsistent set_page_config',
     'Pages 1-10 omit it; 11-17 set it, leading to inconsistent titles. IN PROGRESS 2026.06.30-d: a global .streamlit/config.toml theme now applies to every page regardless, and configure_page() standardizes it on the migrated pages. Remaining pages should adopt configure_page().',
     'Code review: UI'),
    ('health', 'P3', 'Cleanup', 'open', 'Two API entrypoints + partial model registration',
     'app.py wires ~30 routers; main.py re-exports. models/__init__ omits 3 modules that are registered defensively by side-effect imports in app.py -- forget the import and those tables silently never get created.',
     'Code review: API'),

    # ---- IDEAS & ROADMAP -------------------------------------------------
    # Foundation / cleanup
    ('idea', 'P0', 'Methodology', 'done', 'Retire the phase ladder; archive artifacts out of the live tree',
     'DONE 2026-06-30: froze the ladder and archived ~8,135 generated files (scripts/p*_s*, tests/test_p*_s*, packet docs, ui/pages/*Phase*Step*) to archive/ on branch cleanup/retire-phase-ladder. git history/search/bisect usable again. Fully reversible; nothing real deleted.',
     'Synthesis'),
    ('idea', 'P0', 'Cleanup', 'done', 'Collapse routing_bridge_* dead subsystem',
     'DONE 2026-06-30: archived all 32 routing_bridge_* files and de-wired the 24 import/include lines from app.py (127 routes import clean). The one-guarded-module + real-client replacement is only needed if/when a real bridge write-path is required -- deferred, not lost.',
     'Synthesis'),
    ('idea', 'P0', 'Security', 'proposed', 'Add an API auth layer before any deployment',
     'API-key Depends on all mutating/admin/sync routes; gate admin/bootstrap and live-write hardest. Add signature verification to the RingCentral webhook to match FreshBooks/LACRM.',
     'Code review: API'),
    ('idea', 'P1', 'Infra', 'proposed', 'Add CI (GitHub Action running pytest on PR)',
     'Would have made the ladder emptiness obvious. Run the real behavioral tests on every PR; treat existence-check stubs as non-signal or delete them.',
     'Code review: methodology'),
    ('idea', 'P1', 'Data', 'proposed', 'Postgres + Alembic migration path',
     'Phase A of the project own docs roadmap, still undone after 39 phases. Move off single-file SQLite and add schema versioning. Interim: harden SQLite with WAL + busy_timeout.',
     'docs roadmap + review'),
    ('idea', 'P1', 'API', 'proposed', 'Standardize DB access on Depends(get_session)',
     'Convert get_session to a generator dependency and replace the ~200 inline Session(engine) blocks. Unlocks request-scoped transactions and test overrides.',
     'Code review: API'),
    # Core architecture: the connector-first Operations Core (this platform IS the source of truth)
    ('idea', 'P0', 'Architecture', 'proposed', 'Formalize the staged ingestion pipeline (raw -> normalized -> matched -> approved -> applied)',
     'The platform is its OWN source of truth; every external system is a source bucket flowing through controlled stages. app/services/ingestion.py (237 ln) + invoice_ingestion.py (176 ln) already do a staged version. Generalize it into a reusable engine (stages, idempotency keys, approve-to-apply, audit) so every connector (LACRM/RingCentral/FreshBooks/Skimmer/Heritage) shares one spine. Nothing hits canonical tables without an approved delta.',
     'Deep-research rollout report'),
    ('idea', 'P1', 'Intelligence', 'proposed', 'Expected-vs-actual variance + fact-grain engine (the core brain)',
     'Declare fact grains explicitly (chemical/month, labor/visit, margin/invoice, route/time) and build expected + actual fact tables with a variance engine that emits calibration recommendations WITHOUT overwriting baselines. Compare & Train + calibration.py are the seed of this. This is the platform own intelligence layer -- it does NOT depend on Lumen.',
     'Deep-research rollout report'),
    ('idea', 'P1', 'Tools', 'proposed', 'Integrate the pool-volume live tool as a first-class signal generator',
     'The pool_volume_tool_live_proto (references/legacy_seed) hits live GIS/parcel/imagery/geocoder sources and returns volume with evidence + assumptions + confidence. Adapt it into app/tools/pool_volume/, wire endpoints, and persist runs into raw/normalized/tool_run so volume estimates feed chemistry + estimating.',
     'Deep-research rollout report'),
    ('idea', 'P1', 'Connectors', 'done', 'Build out the Skimmer ops/dispatch connector (currently a 1-line stub)',
     'DONE 2026.06.30-g: client + normalizer + raw/normalized/apply pipeline landing work orders as ServiceVisits with labor + chemical actuals (fixture mode now; live when SKIMMER_API_KEY is set). Remaining: apply routes to a route entity, then route-level P&L + expected-vs-actual variance read these actuals.',
     'Deep-research rollout report'),
    ('idea', 'P2', 'Data', 'proposed', 'Postgres schema-per-layer (raw/norm/match/approve/core/fact/audit)',
     'When the Postgres move happens, use a schema-per-layer model in one modular monolith DB, with JSONB for raw payload retention and idempotency + optional outbox as reliability primitives. Enforces the raw->applied contract at the DB boundary.',
     'Deep-research rollout report'),
    # Product features (market-benchmarked)
    ('idea', 'P1', 'Chemistry', 'proposed', 'Port the Key West deterministic chemistry model into versioned code',
     'The Key West consumption-coefficients workbook (monthly climate + rain dilution + dosing rules) already exists under references/legacy_seed and is validated. Port it into app/intelligence/chemistry_keywest.py as a VERSIONED module with the workbook as a regression oracle. This is a port of proven logic, NOT a greenfield feature. Layer an LSI water-balance calc (pH, temp, calcium hardness, alkalinity, CYA, TDS) + dosing recommendations on top. The core product differentiator vs generic field-service tools.',
     'Deep-research rollout report'),
    ('idea', 'P1', 'Operations', 'proposed', 'Route optimization & scheduling',
     'GPS-aware route building to maximize pools serviced per day. Notably, market leader Skimmer lacks this, so it is a real differentiation opportunity. Pairs with job-duration modeling.',
     'Market research'),
    ('idea', 'P1', 'Billing', 'proposed', 'Recurring / automated billing',
     'Automated recurring invoices and payments for maintenance contracts (a 2026 must-have). Build on the existing FreshBooks integration.',
     'Market research'),
    ('idea', 'P2', 'Customer', 'proposed', 'Customer portal',
     'Self-serve portal: service history, water-chemistry readings, invoices/payments, and real-time service updates.',
     'Market research'),
    ('idea', 'P2', 'Field Ops', 'proposed', 'Mobile technician app (PWA)',
     'On-route tech app: route list, photo capture, on-site chemical readings, payment capture. Feeds the LSI engine and the customer portal.',
     'Market research'),
    ('idea', 'P2', 'Connectors', 'proposed', 'QuickBooks sync',
     'The most-requested accounting integration in the category; complements FreshBooks for businesses on QuickBooks Online.',
     'Market research'),
    ('idea', 'P2', 'Analytics', 'proposed', 'Route & customer profitability analytics',
     'Which routes and customers actually make money: margin by route, by tech, by service type. The cost model already exists to support this.',
     'Market research'),
    # AI / automation (2026 trends)
    ('idea', 'P1', 'AI', 'proposed', 'LLM front-desk agent',
     'Autonomous inbound SMS handling: parse intent, propose a booking, confirm, and send 24h/2h reminders. Builds directly on the existing RingCentral -> front-desk -> LACRM skeleton. Gartner expects 40% of enterprise apps to embed task agents by end of 2026.',
     'Market research + AI trends'),
    ('idea', 'P2', 'AI', 'proposed', 'Job-duration modeling for smart scheduling',
     'Learn service-time per property type from historical runs so scheduling uses real durations instead of fixed windows. The data is already captured in estimate/calibration history.',
     'AI trends'),
    ('idea', 'P2', 'AI', 'proposed', 'AI extraction from inbound SMS',
     'Strengthen the existing name/address/intent extraction with an LLM to raise contact-match confidence and cut operator load.',
     'AI trends + review'),
    ('idea', 'P3', 'AI', 'proposed', 'Predictive maintenance & proactive quotes',
     'Use equipment age + service logs to flag likely failures and auto-draft proactive replacement quotes (e.g. a heater nearing end of life).',
     'AI trends'),
    # Connectors / completeness
    ('idea', 'P2', 'Connectors', 'proposed', 'Outbound RingCentral client',
     'Add a RingCentral API client so the platform can send SMS and place calls, closing the comms loop (currently inbound-only).',
     'Code review: services'),
    # Data model / quality
    ('idea', 'P1', 'Data Model', 'proposed', 'Add FKs, enums, and timezone-aware timestamps',
     'Add foreign_key= to parent links, str-backed Enums (or CHECK constraints) for recurring status fields, and standardize on datetime.now(UTC). Removes a whole class of silent data bugs.',
     'Code review: API'),
    ('idea', 'P2', 'Maintainability', 'proposed', 'Move hardcoded catalogs/coefficients into DB/config',
     'Relocate the heater catalog and seed coefficients from source into the existing system_settings / BaselineModelVersion infra. Eliminates the ~1,000-line literal dicts and the dual-edit alias coupling.',
     'Code review: services'),
    ('idea', 'P1', 'Services', 'proposed', 'Wrap multi-write operations in single transactions',
     'Replace per-row commits in loops with one transaction plus rollback, so a partial batch failure rolls back cleanly.',
     'Code review: services'),
    ('idea', 'P2', 'UI', 'in_progress', 'Add a shared UI helper module + error wrapping',
     'ui/_shared.py DONE 2026.06.30-d with configure_page(), page_header(), section(), db_session(). Remaining: migrate all pages to it and add try/except st.error wrapping around DB writes to stop raw tracebacks.',
     'Code review: UI'),

    # ---- LUMEN INTEGRATION (OPTIONAL overlay -- not a dependency) --------
    # This platform is a complete, self-contained Operations Core with its OWN
    # ingestion pipeline and intelligence. Lumen is an optional cross-business
    # overlay for the multi-business owner. Single-platform users lose nothing.
    ('idea', 'P3', 'Lumen Integration', 'proposed', 'Context: Lumen is an optional cross-business overlay, not this platform\'s brain',
     "The pool platform is its own source of truth with its own canonical data + expected-vs-actual intelligence. Lumen (a separate Universal Life OS) can roll this platform up alongside the owner's other businesses for a cross-business view. Integration is a BONUS for the multi-business owner; it is never required and this platform is fully functional without it.",
     'Lumen architecture pass'),
    ('idea', 'P3', 'Lumen Integration', 'proposed', 'Prerequisite: deploy the Lumen backend',
     "Lumen's FastAPI + Postgres + Temporal backend is code-complete but never deployed. Any pool <-> Lumen integration is gated on it running (C:/lumen/03_CURRENT_BUILD/backend/DEPLOY_P0.md, Railway). Read-only; do not modify Lumen code.",
     'Lumen architecture pass'),
    ('idea', 'P3', 'Lumen Integration', 'proposed', 'Phase 0: register the pool business as one Lumen business_id (zero code)',
     "Point Lumen's own FreshBooks + LACRM connectors at the pool business's accounts so Lumen ingests pool invoices/estimates/contacts as canonical objects under one business_id and its cross-business brief lights up. Additive rollup only -- the pool platform's own data + intelligence are unaffected.",
     'Lumen architecture pass'),
    ('idea', 'P3', 'Lumen Integration', 'proposed', 'Phase 1: feed Lumen the data FreshBooks/LACRM do not carry',
     "Service jobs/visits, pool estimate detail, RingCentral comms. Push these to Lumen via its connector -> raw_vault -> canonical_objects path under the pool business_id so Lumen's cross-business rollup is complete. This mirrors -- does not replace -- the pool platform's own canonical store.",
     'Lumen architecture pass'),
    ('idea', 'P3', 'Lumen Integration', 'proposed', 'Integration hygiene: one writer per shared external system + shared JWT',
     "If both apps run, pick ONE writer per external system (FreshBooks/LACRM) to avoid conflicts; the other reads. Keep LACRM as the shared contact record keyed to one stable business_id. Pool platform auths to Lumen via OWNER_API_KEY -> POST /api/auth/token, then Bearer token on sync/events/approvals. Do NOT push pool data as an opaque sync blob -- it never reaches Lumen's canonical layer.",
     'Lumen architecture pass'),
]

_SEED_COLUMNS = ('category', 'priority', 'area', 'status', 'title', 'detail', 'source')

# --------------------------------------------------------------------------
# Seed changelog: the actual build history, newest build last.
# Each tuple: (build, kind, area, title, summary)
# --------------------------------------------------------------------------
DEFAULT_LOG_ENTRIES = [
    # ---- Build 2026.06.30-a : foundation cleanup -------------------------
    ('2026.06.30-a', 'cleanup', 'Methodology', 'Retire the phase-ladder ceremony',
     'Archived ~8,135 auto-generated ladder files (pages/tests/scripts/docs) to archive/ on branch cleanup/retire-phase-ladder. Git history, search, and bisect are usable again. Fully reversible; live tree audited to confirm no real code was swept.'),
    ('2026.06.30-a', 'cleanup', 'API', 'Collapse the routing_bridge dead subsystem',
     'Archived all 32 routing_bridge_* files (19 services + 12 routes + 1 model) and de-wired the 24 import/include lines from app.py. Backend imports clean at 127 routes.'),
    ('2026.06.30-a', 'cleanup', 'UI', 'Prune ui/pages to real pages only',
     'Reduced ui/pages from ~2,046 files to 26 live feature pages. All bridge/Phase packet stragglers archived; the misplaced estimator.py duplicate removed.'),
    ('2026.06.30-a', 'infra', 'Infra', 'Guard backups and long paths',
     'Gitignored backups/ (1,598 folders) and data/*.db + WAL/SHM files. Enabled git core.longpaths for the deep Phase 22 filenames on Windows.'),
    # ---- Build 2026.06.30-b : development tracker -------------------------
    ('2026.06.30-b', 'shipped', 'Development', 'Re-baseline the Development tracker to true scope',
     'Corrected the framing to a self-contained Operations Core (its own ingestion + intelligence; Lumen an optional overlay). Marked cleanup done, reframed chemistry as a port of the Key West model, and added the real-architecture roadmap items.'),
    ('2026.06.30-b', 'shipped', 'Development', 'Add a build-stamped Changelog (this log)',
     'Added a dev_log table + Changelog tab modeled on Lumen\'s build-stamped registry, so every shipped batch is recorded in a clean, time-ordered log and the tracker stays visually organized as we build.'),
    # ---- Build 2026.06.30-c : first real pillar --------------------------
    ('2026.06.30-c', 'shipped', 'Cost Engine', 'True cost-of-doing-business ($/hour) engine',
     'First business pillar. app/services/cost_of_business.py composes burdened wage (payroll tax + benefits) with overhead-per-billable-hour into a fully-loaded cost per field hour -- $46.85/hr at seeded defaults. Workers-comp called out; break-even bill rate at a target margin. New Cost of Business page (18) with live what-if inputs + save-to-settings. 4 tests lock the math (83 -> 87 passing).'),
    # ---- Build 2026.06.30-d : UI polish pass -----------------------------
    ('2026.06.30-d', 'refactor', 'UI', 'Streamlit polish pass: global theme + shared components',
     'Added .streamlit/config.toml (light, teal/water accent) that themes every page, a ui/_shared.py (configure_page, page_header, section, db_session) with a CSS refinement that styles metrics as clean stat cards, and made ui an importable package. Converted Dashboard, Development, and Cost of Business to the shared header/theme. Moves toward closing two logged UI health findings. 87/87 tests still pass.'),
    # ---- Build 2026.06.30-e : purchasing intelligence --------------------
    ('2026.06.30-e', 'shipped', 'Purchasing', 'Purchasing intelligence: best source + price anomalies',
     'app/services/purchasing.py turns the ProductPriceHistory ledger into decisions: a supplier price book per product, best-source recommendation with the cross-vendor spread you are leaving on the table, and price-anomaly flags (a vendor\'s latest cost jumping vs its own previous). New Purchasing page (19) with best-source table, per-product price book, anomaly list, and manual price entry. No new tables -- pure analytics over the existing ledger. 4 tests lock the logic (87 -> 91 passing).'),
    # ---- Build 2026.06.30-f : asset lifecycle registry -------------------
    ('2026.06.30-f', 'shipped', 'Assets', 'Asset lifecycle registry (ordered -> received -> installed -> retired)',
     'New AssetRecord table + app/services/assets.py track a physical item (pump, heater, filter...) through its lifecycle with serial/model numbers, purchase provenance (vendor/invoice/cost/date), install location (property + vessel), and warranty. asset_summary rolls up installed-base value + warranties expiring soon. New Assets page (20): filterable registry, per-property asset list, add form, and receive/install/retire actions. Confirmed invoice ingestion already feeds the price ledger, so Purchasing self-populates. 3 tests lock the lifecycle (91 -> 94 passing).'),
    # ---- Build 2026.06.30-g : Skimmer ops connector ---------------------
    ('2026.06.30-g', 'shipped', 'Connectors', 'Skimmer ops connector (client + normalizer + pipeline ingestion)',
     'Built the Skimmer connector on the raw -> normalized -> applied pipeline: SkimmerClient (skimmer-api-key header) with a fixture fallback so it runs before live creds; normalizers for customers/service-locations/bodies-of-water/work-orders/routes; and sync_skimmer() that lands service locations as Properties, bodies of water as PoolVessels, and work orders as ServiceVisits with ActualLaborFact + ActualChemicalFact + TechnicianAssignment (chemicals matched to seeded products). Idempotent. New Skimmer page (21): connection status, one-click sync, imported-visit table, run history. Drop in SKIMMER_API_KEY to go live. 4 tests (94 -> 98 passing). Unlocks route P&L + expected-vs-actual variance.'),
    # ---- Build 2026.06.30-h : customer identity matching ----------------
    ('2026.06.30-h', 'shipped', 'Identity', 'Three-pass customer matching engine + manual review',
     'New CustomerProfile + CustomerMatch tables and app/services/customer_matching.py resolve external customer records (Skimmer, FreshBooks) to one internal account: pass 1 exact email auto-links, pass 2 exact phone / strong fuzzy name auto-links, pass 3 ambiguous ones land in a manual queue; genuinely new customers get a fresh account. confirm_match/unlink_match let a human override anytime and decisions persist (low-maintenance for a stable client base). Skimmer sync now resolves customers into per-customer accounts (not a catch-all) so cost lands on the right identity. New Customer Matching page (22): review queue + all-matches table + override. Phone normalized to last 10 digits. 5 tests (98 -> 103). Sets up FreshBooks revenue to join Skimmer cost.'),
]

_LOG_COLUMNS = ('build', 'kind', 'area', 'title', 'summary')


# --------------------------------------------------------------------------
# Persistence helpers
# --------------------------------------------------------------------------
def _spec_to_kwargs(spec: tuple) -> dict:
    return dict(zip(_SEED_COLUMNS, spec))


def seed_if_empty(session: Session) -> int:
    """Populate the tracker with the default review on first run only."""
    if session.exec(select(DevItem)).first() is not None:
        return 0
    for spec in DEFAULT_DEV_ITEMS:
        session.add(DevItem(**_spec_to_kwargs(spec)))
    session.commit()
    return len(DEFAULT_DEV_ITEMS)


def add_missing_defaults(session: Session) -> int:
    """Non-destructively re-add any default item whose title is not already present."""
    existing_titles = {row.title for row in session.exec(select(DevItem)).all()}
    added = 0
    for spec in DEFAULT_DEV_ITEMS:
        kwargs = _spec_to_kwargs(spec)
        if kwargs['title'] not in existing_titles:
            session.add(DevItem(**kwargs))
            added += 1
    if added:
        session.commit()
    return added


# Rows the user created carry these sources; everything else is a seeded review row.
_MANUAL_SOURCES = {'user', 'manual'}


def rebuild_defaults(session: Session) -> tuple[int, int]:
    """Re-baseline: delete seeded review rows and re-insert the current defaults.

    Preserves user-added rows (source in _MANUAL_SOURCES). Use after the default
    content changes. Returns (removed, inserted).
    """
    removed = 0
    for row in session.exec(select(DevItem)).all():
        if row.source not in _MANUAL_SOURCES:
            session.delete(row)
            removed += 1
    for spec in DEFAULT_DEV_ITEMS:
        session.add(DevItem(**_spec_to_kwargs(spec)))
    session.commit()
    return removed, len(DEFAULT_DEV_ITEMS)


def seed_log_if_empty(session: Session) -> int:
    """Populate the changelog with the real build history on first run only."""
    if session.exec(select(DevLogEntry)).first() is not None:
        return 0
    for spec in DEFAULT_LOG_ENTRIES:
        session.add(DevLogEntry(**dict(zip(_LOG_COLUMNS, spec))))
    session.commit()
    return len(DEFAULT_LOG_ENTRIES)


def add_missing_log_entries(session: Session) -> int:
    """Non-destructively add any seed log entry whose (build, title) is not present."""
    existing = {(r.build, r.title) for r in session.exec(select(DevLogEntry)).all()}
    added = 0
    for spec in DEFAULT_LOG_ENTRIES:
        kwargs = dict(zip(_LOG_COLUMNS, spec))
        if (kwargs['build'], kwargs['title']) not in existing:
            session.add(DevLogEntry(**kwargs))
            added += 1
    if added:
        session.commit()
    return added


def load_log(session: Session) -> list[DevLogEntry]:
    """All changelog entries, newest build first (then newest entry first)."""
    rows = list(session.exec(select(DevLogEntry)).all())
    rows.sort(key=lambda r: (r.build, r.id or 0), reverse=True)
    return rows


def load_items(session: Session, category: str) -> list[DevItem]:
    rows = list(session.exec(select(DevItem).where(DevItem.category == category)).all())
    if category == 'feature':
        rows.sort(key=lambda r: (FEATURE_STATUS_RANK.get(r.status, 9), r.area, r.title))
    else:
        rows.sort(key=lambda r: (PRIORITY_RANK.get(r.priority, 9), r.status, r.area))
    return rows


def persist_edits(session: Session, category: str, original: list[DevItem], edited: pd.DataFrame) -> tuple[int, int, int]:
    """Upsert the edited grid back into the DB. Returns (updated, inserted, deleted)."""
    by_id = {item.id: item for item in original}
    seen: set[int] = set()
    updated = inserted = 0

    for _, row in edited.iterrows():
        title = str(row.get('title') or '').strip()
        if not title:
            continue  # blank title -> treated as a removed row
        rid = row.get('id')
        area = (str(row.get('area') or 'General').strip() or 'General')
        status = str(row.get('status') or DEFAULT_STATUS[category]).strip()
        priority = str(row.get('priority') or 'P2').strip()
        detail = str(row.get('detail') or '')
        source = str(row.get('source') or '')

        if pd.notna(rid) and int(rid) in by_id:
            item = by_id[int(rid)]
            changed = (
                item.title != title or item.area != area or item.status != status
                or item.priority != priority or item.detail != detail or item.source != source
            )
            if changed:
                item.title, item.area, item.status = title, area, status
                item.priority, item.detail, item.source = priority, detail, source
                item.updated_at = datetime.utcnow()
                session.add(item)
                updated += 1
            seen.add(int(rid))
        else:
            session.add(DevItem(
                category=category, title=title, area=area, status=status,
                priority=priority, detail=detail, source=source or 'manual',
            ))
            inserted += 1

    deleted = 0
    for rid, item in by_id.items():
        if rid not in seen:
            session.delete(item)
            deleted += 1

    session.commit()
    return updated, inserted, deleted


# --------------------------------------------------------------------------
# Page
# --------------------------------------------------------------------------
create_db_and_tables()
with Session(engine) as _seed_session:
    seed_if_empty(_seed_session)
    seed_log_if_empty(_seed_session)

page_header(
    'Development Tracker',
    f'Living record of what works, what needs fixing, and what to build next · Build {DEV_BUILD} · Edit any cell, add rows, then Save.',
    icon='🧱',
)

with Session(engine) as session:
    all_items = list(session.exec(select(DevItem)).all())
    log_entries = load_log(session)

features = [i for i in all_items if i.category == 'feature']
health = [i for i in all_items if i.category == 'health']
ideas = [i for i in all_items if i.category == 'idea']
builds_shipped = len({e.build for e in log_entries if e.build})

working = sum(1 for i in features if i.status == 'working')
health_open = sum(1 for i in health if i.status in ('open', 'in_progress'))
p0_open = sum(1 for i in health if i.status in ('open', 'in_progress') and i.priority == 'P0')
ideas_open = sum(1 for i in ideas if i.status in ('proposed', 'planned', 'in_progress'))

c1, c2, c3, c4, c5, c6 = st.columns(6)
c1.metric('Working features', working, help='Features with status "working" (partial/stub excluded).')
c2.metric('Health findings open', health_open, help='Code-health items still open or in progress.')
c3.metric('P0 critical open', p0_open, help='Critical findings (security, ceremony, dead subsystems) still open.')
c4.metric('Ideas in play', ideas_open, help='Roadmap ideas proposed, planned, or in progress.')
c5.metric('Builds shipped', builds_shipped, help='Distinct builds recorded in the changelog.')
c6.metric('Total tracked', len(all_items), help='All tracked items across every category.')

st.divider()

tab_overview, tab_changelog, tab_features, tab_health, tab_ideas, tab_add = st.tabs(
    ['Overview & assessment', 'Changelog', 'Working features', 'Code health', 'Ideas & roadmap', 'Add item']
)


def render_category_tab(category: str) -> None:
    title, blurb = CATEGORY_META[category]
    st.subheader(title)
    st.caption(blurb)

    with Session(engine) as sess:
        items = load_items(sess, category)

    if items:
        df = pd.DataFrame([{
            'id': it.id,
            'priority': it.priority,
            'status': it.status,
            'area': it.area,
            'title': it.title,
            'detail': it.detail,
            'source': it.source,
        } for it in items])
    else:
        df = pd.DataFrame(columns=['id', 'priority', 'status', 'area', 'title', 'detail', 'source'])

    edited = st.data_editor(
        df,
        width='stretch',
        hide_index=True,
        num_rows='dynamic',
        key=f'editor_{category}',
        column_config={
            'id': st.column_config.NumberColumn('ID', disabled=True, width='small'),
            'priority': st.column_config.SelectboxColumn('Priority', options=PRIORITY_OPTIONS, width='small'),
            'status': st.column_config.SelectboxColumn('Status', options=STATUS_BY_CATEGORY[category], width='small'),
            'area': st.column_config.TextColumn('Area', width='small'),
            'title': st.column_config.TextColumn('Title', width='large'),
            'detail': st.column_config.TextColumn('Detail', width='large'),
            'source': st.column_config.TextColumn('Source', width='medium'),
        },
    )

    col_save, col_note = st.columns([1, 4])
    with col_save:
        if st.button('Save changes', type='primary', key=f'save_{category}'):
            with Session(engine) as sess:
                items = load_items(sess, category)  # reload originals for a clean diff
                updated, inserted, deleted = persist_edits(sess, category, items, edited)
            st.success(f'Saved. {updated} updated, {inserted} added, {deleted} removed.')
            st.rerun()
    with col_note:
        st.caption('Tip: edit cells inline, add rows at the bottom, or clear a Title to remove a row. New rows inherit this tab category.')


def render_changelog_tab() -> None:
    st.subheader('Changelog')
    st.caption('Time-ordered record of what actually shipped, grouped by build. Newest first. '
               'Modeled on the Lumen development registry so progress stays visually organized.')

    with st.expander('Add a changelog entry'):
        with st.form('add_log_form', clear_on_submit=True):
            la, lb, lc = st.columns(3)
            with la:
                l_build = st.text_input('Build', value=DEV_BUILD)
            with lb:
                l_kind = st.selectbox('Kind', options=KIND_OPTIONS,
                                      format_func=lambda k: f'{KIND_META[k][0]} {KIND_META[k][1]}')
            with lc:
                l_area = st.text_input('Area', value='General')
            l_title = st.text_input('Title')
            l_summary = st.text_area('Summary', height=80)
            if st.form_submit_button('Add entry', type='primary'):
                if not l_title.strip():
                    st.error('Title is required.')
                else:
                    with Session(engine) as sess:
                        sess.add(DevLogEntry(
                            build=(l_build.strip() or DEV_BUILD), kind=l_kind,
                            area=(l_area.strip() or 'General'),
                            title=l_title.strip(), summary=l_summary.strip(),
                        ))
                        sess.commit()
                    st.success('Logged.')
                    st.rerun()

    with Session(engine) as sess:
        entries = load_log(sess)

    if not entries:
        st.info('No changelog entries yet. Add one above, or use the maintenance button to seed the build history.')
        return

    current_build = None
    for e in entries:
        if e.build != current_build:
            current_build = e.build
            count = sum(1 for x in entries if x.build == e.build)
            st.markdown(f'### Build {e.build or "(unstamped)"}  ·  {count} change{"s" if count != 1 else ""}')
            st.divider()
        emoji, label = KIND_META.get(e.kind, ('•', e.kind))
        st.markdown(f'{emoji}  **{e.title}**  ·  `{label}`  ·  _{e.area}_')
        if e.summary:
            st.caption(e.summary)


with tab_changelog:
    render_changelog_tab()

with tab_features:
    render_category_tab('feature')

with tab_health:
    render_category_tab('health')

with tab_ideas:
    render_category_tab('idea')

with tab_add:
    st.subheader('Add a tracked item')
    st.caption('Capture a new feature, finding, or idea the moment you think of it.')
    with st.form('add_item_form', clear_on_submit=True):
        fa, fb, fc = st.columns(3)
        with fa:
            in_category = st.selectbox('Category', options=['idea', 'health', 'feature'],
                                       format_func=lambda c: CATEGORY_META[c][0])
        with fb:
            in_priority = st.selectbox('Priority', options=PRIORITY_OPTIONS, index=2)
        with fc:
            in_area = st.text_input('Area', value='General')
        in_title = st.text_input('Title')
        in_detail = st.text_area('Detail', height=100)
        in_source = st.text_input('Source', value='user')
        submitted = st.form_submit_button('Add item', type='primary')
        if submitted:
            if not in_title.strip():
                st.error('Title is required.')
            else:
                with Session(engine) as sess:
                    sess.add(DevItem(
                        category=in_category,
                        title=in_title.strip(),
                        area=(in_area.strip() or 'General'),
                        status=DEFAULT_STATUS[in_category],
                        priority=in_priority,
                        detail=in_detail.strip(),
                        source=(in_source.strip() or 'user'),
                    ))
                    sess.commit()
                st.success(f'Added to {CATEGORY_META[in_category][0]}.')
                st.rerun()

    st.divider()
    st.markdown('**Maintenance**')
    mcol1, mcol2, mcol3 = st.columns(3)
    with mcol1:
        if st.button('Re-add missing defaults (non-destructive)'):
            with Session(engine) as sess:
                added = add_missing_defaults(sess)
            st.success(f'Added {added} missing default item(s).' if added else 'All default items already present.')
            st.rerun()
        if st.button('Add missing changelog entries'):
            with Session(engine) as sess:
                added = add_missing_log_entries(sess)
            st.success(f'Added {added} changelog entr(ies).' if added else 'Changelog already up to date.')
            st.rerun()
    with mcol2:
        st.caption('Re-baseline replaces the seeded review with the current corrected defaults. Your manually added rows are kept.')
        if st.button('Re-baseline from corrected defaults', type='primary'):
            with Session(engine) as sess:
                removed, inserted = rebuild_defaults(sess)
            st.success(f'Re-baselined: removed {removed} seeded rows, inserted {inserted} current defaults. Manual rows preserved.')
            st.rerun()
    with mcol3:
        export_df = pd.DataFrame([{
            'category': i.category, 'priority': i.priority, 'status': i.status,
            'area': i.area, 'title': i.title, 'detail': i.detail, 'source': i.source,
        } for i in all_items])
        st.download_button(
            'Export all items (CSV)',
            data=export_df.to_csv(index=False).encode('utf-8'),
            file_name='development_tracker.csv',
            mime='text/csv',
        )


with tab_overview:
    st.subheader('Code-appropriateness assessment')
    st.caption('Verdict from a full four-part code review on 2026-06-30, with 2026 market and AI grounding.')

    st.markdown(
        '**What this is:** a self-contained **Unified Pool Service Operations Core** -- it is its OWN '
        'source of truth, with its own staged ingestion pipeline (raw -> normalized -> matched -> approved '
        '-> applied), its own connectors (LACRM, RingCentral, FreshBooks, Skimmer, Heritage), and its own '
        'deterministic intelligence (chemistry model, pool-volume signal generator, expected-vs-actual '
        'variance/calibration). Some users will run only this platform and get the complete product. Lumen '
        'is an OPTIONAL cross-business overlay, not a dependency.'
    )

    st.markdown(
        '**Bottom line:** a genuinely good product core. The estimation engine, heater-sizing math, '
        'quote-workflow state machine, staged ingestion, and the FreshBooks/LACRM/RingCentral/Heritage '
        'connectors are real, thoughtful engineering. It was buried under a "phase ladder" that generated '
        '~8,000 ceremony files -- now archived (2026-06-30). What remains is finishing the real intelligence '
        'layer and hardening for deployment.'
    )

    st.markdown('**Status of the three biggest problems**')
    st.markdown(
        '1. **Retire the phase ladder.** DONE 2026-06-30 -- ~8,135 ceremony files archived to archive/ on '
        'branch cleanup/retire-phase-ladder; git history/search usable again. Fully reversible.\n'
        '2. **Add authentication.** STILL OPEN -- no auth anywhere in the API; every endpoint (incl. DB '
        're-seed and live-write sync) is public. Must land before any deployment.\n'
        '3. **Collapse routing_bridge_*.** DONE 2026-06-30 -- all 32 files archived and de-wired from app.py.'
    )

    st.markdown('**Architecture grades by area**')
    grades = pd.DataFrame([
        {'Area': 'Estimation engine', 'Grade': 'A-', 'Note': 'Data-driven, versioned, closes a calibration loop. Magic seed numbers.'},
        {'Area': 'Quote workflow', 'Grade': 'A-', 'Note': 'Clean state machine, enforced transitions, good Pydantic validation.'},
        {'Area': 'Connectors (FB/LACRM)', 'Grade': 'B+', 'Note': 'Real clients, signed webhooks, dry-run gating. Plaintext tokens.'},
        {'Area': 'Front desk / comms', 'Grade': 'B', 'Note': 'Works; god module; RingCentral is inbound-only.'},
        {'Area': 'API design', 'Grade': 'C', 'Note': 'Clean route/service split, but no auth, no DI, some untyped bodies.'},
        {'Area': 'Data model', 'Grade': 'C', 'Note': 'Pragmatic and indexed, but no FKs/enums, CSV-in-column, naive datetimes.'},
        {'Area': 'Security', 'Grade': 'D', 'Note': 'No auth, plaintext secrets, one unsigned webhook.'},
        {'Area': 'Testing', 'Grade': 'D', 'Note': 'Real tests are excellent but ~1.3% of the suite; no CI.'},
        {'Area': 'UI / Streamlit', 'Grade': 'B-', 'Note': 'Cleaned 2026-06-30: 26 real pages, junk archived. Still no error handling / shared helpers.'},
        {'Area': 'Build methodology', 'Grade': 'C', 'Note': 'Phase ladder retired 2026-06-30 (archived). Now needs CI + real behavioral tests to replace the empty ones.'},
    ])
    st.dataframe(grades, width='stretch', hide_index=True)

    st.markdown('**Suggested order of work**')
    st.markdown(
        '1. ~~Archive the phase ladder and routing_bridge_* tree.~~ DONE 2026-06-30.\n'
        '2. Add API auth + CI running the real tests (highest-priority remaining foundation item).\n'
        '3. Harden SQLite (WAL + busy_timeout) as a stopgap, then execute the Postgres + Alembic + '
        'schema-per-layer move (the strategic fix -- SQLite\'s single-writer limit becomes a wall once '
        'UI + connectors + jobs write concurrently).\n'
        '4. Standardize DB sessions on Depends(get_session); add FKs/enums.\n'
        '5. Formalize the staged ingestion pipeline as the shared connector spine.\n'
        '6. Port the Key West deterministic chemistry model + build the expected-vs-actual variance engine '
        '(the core intelligence layer) and integrate the pool-volume tool.\n'
        '7. Build out the Skimmer ops connector, then route optimization, recurring billing, and the '
        'LLM front-desk agent.'
    )

    st.info(
        'Market & AI sources (2026): PoolDial and Skimmer software comparisons; PoolFounder buying guide; '
        'Makula and FieldCamp on AI in field service; Orenda on the Langelier Saturation Index. '
        'LSI chemical tracking is the feature that most separates pool-specific software from generic tools; '
        'route optimization is a gap even in the market leader (Skimmer).'
    )
