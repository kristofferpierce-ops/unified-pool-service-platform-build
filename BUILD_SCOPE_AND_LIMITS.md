# Build scope and limits

This package is a real code build, but it is **not** the final finished production platform.

What is implemented now:
- merged backbone from the uploaded platform repo
- connector-first staging tables
- communications domain tables
- RingCentral normalization and ingest path
- front desk approval and task queue APIs
- persisted labor settings
- legacy reference material included inside the repo

What remains for the next phase:
- Postgres + Alembic migration path
- real OAuth and webhook token handling for live connectors
- invoice pipeline refactor onto generic staging models
- workbook-port deterministic chemistry engine
- Skimmer, FreshBooks, and Heritage production connectors
- branch overlays and variance fact persistence
- front desk UI port from the bridge into the unified UI shell
