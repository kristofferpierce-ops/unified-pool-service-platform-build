# Pool Service Pricing Platform v1

Residential-first Python application for estimating the **real servicing cost** of a pool.

This starter build separates:
- shared company costs
- baseline chemistry model versions
- property/account records
- saved estimate scenarios
- actual field observations
- estimate-vs-actual comparison and training workflows

## Stack
- **Streamlit** for the internal UI
- **FastAPI** for a forward-compatible backend API layer
- **SQLModel + SQLite** for persistent storage

## Main design goals
1. Keep the **baseline estimate environment** isolated from real-world observations.
2. Keep the **expense engine** reusable so residential and commercial models can share the same backend.
3. Allow multiple estimate scenarios per property.
4. Preserve version history so future model revisions do not corrupt old estimates.

## Project layout
- `app/core` database and configuration
- `app/models` SQLModel tables
- `app/services` calculation and persistence logic
- `app/api` FastAPI entry point and routes
- `ui/app.py` Streamlit user interface
- `scripts/seed_database.py` initial data seeding

## Quick start
```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python scripts/seed_database.py
streamlit run ui/app.py
```

Optional API server:
```bash
uvicorn app.api.main:app --reload
```

## Core concepts
### Shared cost database
Company costs, chemical unit costs, labor settings, and other reusable admin data live in the database and are shared by all future pricing models.

### Baseline model versions
A baseline model version holds climate assumptions, water assumptions, chemical coefficients, and weighting rules. Each estimate stores the exact model version it used.

### Property and scenario separation
A property can have multiple saved scenarios, for example:
- baseline quote
- conservative quote
- aggressive quote
- calibrated quote

### Training isolation
Actual observations do **not** overwrite the baseline model. They are stored separately and compared against the saved estimate runs.

## What v1 already includes
- editable company expense table
- editable labor settings and chemical costs
- editable baseline chemical coefficients
- editable weighting model for bathing load, tree/debris, and filtration quality
- property records with address and route assumptions
- saved estimate scenarios
- field observations with actual chemistry and labor inputs
- estimate vs actual comparison page

## What is intentionally left ready for expansion
- commercial pool model modules
- route clustering / dispatch support
- weather API integration
- account-specific machine learning or calibration suggestions
- quote templates and PDF exports
