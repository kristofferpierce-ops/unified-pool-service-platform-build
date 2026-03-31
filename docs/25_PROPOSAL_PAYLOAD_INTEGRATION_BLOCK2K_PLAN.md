# Block 2K · Proposal payload integration

## Goal
Create one service-layer proposal payload that can reuse attached package lines and customer-safe proposal text in the FreshBooks draft flow.

## Scope
- Add `build_quote_case_proposal_payload(...)` in `app/services/heater_quote.py`
- Reuse proposal-ready package summary and attached package lines
- Feed package-derived customer notes into `app/services/freshbooks_sync.py` when no explicit notes are supplied
- Add a preview in `ui/pages/11_Quote_Workflow.py`
- Add targeted tests for payload cleanliness and FreshBooks draft notes

## Acceptance
- Package-backed quote cases build a reusable proposal payload
- Customer proposal text excludes selector scoring
- FreshBooks draft notes can reuse package-derived proposal text
- Existing draft line fallback behavior stays intact
