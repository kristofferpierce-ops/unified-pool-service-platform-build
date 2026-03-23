# Pool Service Pricing Platform v2

Residential and commercial pricing platform for pool-service estimating, cost allocation, chemical modeling, invoice ingestion, direct-delivery tracking, and estimate-vs-actual calibration.

## What this build includes

- Shared admin cost database for insurance, vehicle, supplies, office, software, admin, and future expenses
- Separate residential and commercial account handling on the same cost backbone
- Baseline chemistry model versions isolated from real-world observations
- Multiple saved estimate scenarios per property
- Commercial vendor orders, direct deliveries, received-confirmation status, and discrepancy tracking
- Invoice ingestion staging with three review buckets:
  - high_confidence
  - assisted_match
  - exception
- Product-price history updates through approval workflow instead of direct overwrite
- Estimate-vs-actual comparison and account-specific calibration suggestions
- Monthly commercial direct-delivery billing report with Excel export
- Tools section with a property-authority verification workflow and approved-agent records

## Stack

- Python 3.11+
- Streamlit for the UI
- FastAPI for the API layer
- SQLModel / SQLAlchemy with SQLite by default
- Pandas + OpenPyXL for reports and exports
- PyPDF for simple invoice text extraction

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python scripts/init_db.py
streamlit run ui/app.py
```

Optional API server:

```bash
uvicorn app.api.main:app --reload
```

## Notes

This is a forward-focused starter codebase. Residential and commercial share core settings while training separate model families. The baseline model is intentionally isolated from field observations. Invoices never write directly into the master database.


## Tools architecture

The app now includes a dedicated Tools page so office workflows can grow without bloating the estimator pages. The first tool is a property-authority verification workflow for intake screening. It stores verification cases, approved agents, and tool runs separately from pricing and training data so future tools can use the same framework without corrupting the baseline model.
