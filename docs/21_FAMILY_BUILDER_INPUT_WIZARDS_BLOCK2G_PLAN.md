# Block 2G - Family Builder Input Wizards

This slice adds structured input wizards for the equipment package families already supported by the generic package workspace.

Families covered:
- pump
- filter
- salt_system
- automation

What this block adds:
- wizard catalog for each family with structured fields
- service helpers to derive builder profile, equipment label, and builder options from wizard inputs
- preview and save flows for wizard-generated templates
- route endpoints for wizard catalog, preview, and save
- quote workflow UI for creating reusable templates from structured wizard inputs
- tests for wizard catalog, preview, save, and apply flows

What this block does not do:
- add vendor live-product lookup for non-heater families
- change FreshBooks draft logic
- add new database tables

Expected verification:
- heater test file grows and stays green
- full suite stays green
- quote workflow can create and apply wizard-generated templates for all supported families
