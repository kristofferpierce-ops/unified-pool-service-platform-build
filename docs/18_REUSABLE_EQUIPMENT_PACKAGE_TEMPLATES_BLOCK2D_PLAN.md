
# Block 2D - Reusable equipment package templates

This block adds a reusable template layer on top of the quote package workspace.

## Scope
- Save an attached heater package as a reusable equipment package template
- List saved templates
- Apply a saved template to a quote case
- Delete a saved template
- Keep the same attached package structure so FreshBooks draft generation continues to work without special-case logic

## Notes
- Templates are stored in system settings under `equipment_package_templates`
- This keeps the block lightweight and avoids a database migration
- The structure is intentionally generic enough to support non-heater equipment packages later
