# Phase 19 Step 13 — Text Quality Workbench

Step 13 adds display-only text quality diagnostics for bridge-origin SMS records.

## Goals

- Detect legacy mojibake such as `donât`, malformed smart quotes, and common malformed emoji byte sequences.
- Provide display-cleaned previews without mutating raw RingCentral, bridge, or platform records.
- Add API endpoints and a Streamlit page for operator-facing text quality review.

## New endpoints

- `GET /front-desk/text-quality/summary`
- `GET /front-desk/text-quality/samples`

## New Streamlit page

- `ui/pages/16_Text_Quality.py`

## Safety

This step is read-only and display-only. It does not write to LACRM, RingCentral, bridge state, or SMS raw payloads.
