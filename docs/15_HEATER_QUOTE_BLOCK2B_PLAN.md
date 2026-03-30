# Heater Quote Block 2B

This block extends the Block 2A heater module into the quote workflow and FreshBooks draft flow.

## Goals

- turn a heater recommendation into a reusable install package
- let staff preview equipment, materials, allowance, and labor lines before attaching them
- store prepared package lines on the quote case through the existing external-link ledger
- let FreshBooks draft creation use attached heater package lines automatically when no manual draft lines are supplied

## Scope

### Heater package builder
- package profile selection such as gas standard or heat pump standard
- labor profile selection such as standard, simple swap, or tight access
- optional scope toggles for bypass kit, pad kit, gas allowance, electrical allowance, automation integration, and startup visit
- miscellaneous materials allowance override
- package total preview

### Quote workflow attachment
- attach a full prepared heater package to a quote case
- keep the prepared lines in the heater quote external-link payload so the package can be reused later

### FreshBooks draft flow
- when staff create a FreshBooks draft without manual lines, the draft service now uses attached heater package lines automatically
- if staff still pass manual lines explicitly, those manual lines remain the source of truth for that draft request

## Design notes

- no database migration is required for this block
- the package lines live in the existing quote-case external-link payload JSON
- this keeps the feature reversible and easier to refine without changing the schema

## Expected verification

- heater quote package preview works in the UI
- attaching a heater package returns prepared lines and package totals
- FreshBooks dry-run draft creation without explicit lines uses the attached heater package lines
