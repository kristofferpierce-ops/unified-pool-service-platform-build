# Block 2C.1 - Quote Package Workspace

This block turns the existing heater package attachment flow into a visible quote-case workspace feature.

## Goals

- Show attached heater/equipment packages directly in the quote workflow case view.
- Show case-level package totals for equipment, labor, materials, and grand total.
- Allow staff to remove an attached package from a quote case.
- Allow the heater quote page to replace existing attached heater packages on a quote case in one action.
- Keep the package structure reusable for future tools such as pumps, filters, automation, and salt systems.

## Scope

### Service layer
- Add a package workspace summary for quote cases.
- Add package removal support.
- Add optional replace-existing behavior to heater package attachment.

### API layer
- Add heater quote package workspace endpoints.
- Add delete endpoint for attached heater packages.
- Extend attach payload with `replace_existing`.

### UI layer
- Quote Workflow page shows package count and package total for each case.
- Quote Workflow page shows attached package detail rows and line items.
- Quote Workflow page can remove attached packages.
- Heater Quote page can replace existing heater packages on the selected quote case.

## Acceptance target

- Attach a heater package to a quote case.
- See the package and totals inside the quote workflow case panel.
- Remove the package from the quote workflow page.
- Replace the existing package from the heater quote page.
- Preserve FreshBooks draft behavior that uses attached package lines.
