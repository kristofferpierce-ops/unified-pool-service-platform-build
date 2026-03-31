# Block 2H: Catalog-backed selectors and compatibility rules

This block adds a selector layer on top of the generic equipment package families.

## Goals

- Add normalized selector catalogs for pump, filter, salt system, and automation families.
- Let staff choose a specific selector item instead of only using a freeform builder or wizard.
- Evaluate compatibility rules before saving a reusable template.
- Build package previews from selector choices using the existing package builder pipeline.
- Keep applied packages, quote workspace, overrides, and FreshBooks draft handoff on the same attached package system already in place.

## Included behaviors

- Selector catalog endpoint
- Selector preview endpoint
- Selector template creation endpoint
- Quote Workflow UI for selector-driven template creation
- Compatibility warnings and hard blockers on save
- Tests covering selector catalog, incompatible preview, selector template save, and selector template apply

## Families covered

- pump
- filter
- salt_system
- automation

## Notes

This is intentionally a normalized internal selector layer, not a direct live vendor catalog implementation. It is designed so that future live or synchronized product catalogs can map into the same selector structure without changing the quote package workspace or FreshBooks line generation flow.
