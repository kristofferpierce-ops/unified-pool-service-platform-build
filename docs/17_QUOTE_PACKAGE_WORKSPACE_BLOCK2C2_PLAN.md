# Block 2C.2 - Quote package line overrides and FreshBooks precedence

## Purpose
Turn the attached heater package into an editable quote-case package workspace.

## Scope
- Edit attached heater package lines directly from the Quote Workflow page
- Save quote-case-specific line overrides without deleting the original attached package
- Reset package lines back to the original attached package lines
- Expose workspace update and reset routes under the heater quote API
- Make FreshBooks draft generation keep using attached package lines, which now include overrides when present

## Files changed
- app/services/heater_quote.py
- app/api/routes/heater_quotes.py
- ui/pages/11_Quote_Workflow.py
- tests/test_heater_quote.py
- tests/test_freshbooks_sync.py

## Acceptance target
- A quote case with an attached heater package shows editable package lines
- Saving overrides updates the package workspace totals and marks the package as overridden
- Reset restores the original attached package lines
- FreshBooks draft generation uses the edited package lines when manual draft lines are not supplied
