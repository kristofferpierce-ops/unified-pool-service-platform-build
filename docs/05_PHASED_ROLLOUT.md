# Phased rollout map

## Phase A: foundation hardening
- move to Postgres
- add Alembic
- standardize FastAPI entrypoint
- normalize config loading
- remove operational dependence on SQLite

## Phase B: universal ingestion core
- create source registry
- create connector run logging
- create raw record storage
- create normalized record storage
- create match candidate queue
- create approval decision queue
- create apply event log
- refactor invoice ingestion into this framework first

## Phase C: deterministic intelligence
- port workbook formulas into versioned code
- define expected fact grains
- define actual fact grains
- add variance engine
- add calibration suggestions as explicit artifacts
- absorb pool volume tool as evidence-producing internal tool

## Phase D: intake and communications connectors
- absorb bridge logic into RingCentral connector
- absorb bridge logic into LACRM connector
- create communication event domain
- build front desk review queue inside the unified platform

## Phase E: billing connector
- FreshBooks client, invoice, payment, and line sync
- expected versus billed versus paid reconciliation

## Phase F: operations connector
- Skimmer customer, location, body of water, work order, and route sync
- actual labor and chemical observation capture

## Phase G: product cost and branch overlays
- Heritage product and cost import using staged file or API contracts
- branch overlays for costs, climate, pricing, and profitability segmentation

## Phase H: probabilistic layer later
- Bayesian updates only after stable deterministic observations exist
- recommendation engine after attribution and variance loops are working
