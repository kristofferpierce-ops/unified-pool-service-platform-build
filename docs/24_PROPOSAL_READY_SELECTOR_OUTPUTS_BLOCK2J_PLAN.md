# Block 2J · Proposal-Ready Selector Outputs

This slice builds on the green selector-ranking state and adds customer-facing proposal outputs for attached equipment packages.

## Scope
- Proposal-ready package summaries for quote cases
- Customer-facing package text separated from internal review notes
- Internal selector score, branch preference, and compatibility review retained for staff only
- Quote Workflow UI section for customer summary download and internal review

## Files
- app/services/heater_quote.py
- ui/pages/11_Quote_Workflow.py
- tests/test_heater_quote.py

## Acceptance
- Attached packages can be rendered into customer-facing package summaries
- Internal review shows selector score, branch choice, and compatibility counts
- Customer-facing summary hides internal scoring text
- Full suite remains green after patch apply
