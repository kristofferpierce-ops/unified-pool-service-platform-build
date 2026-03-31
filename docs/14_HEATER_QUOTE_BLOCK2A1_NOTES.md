# Heater Quote Block 2A.1

This patch improves the first heater quote module in three areas:

- adds a starter fallback planning catalog so the tool no longer returns an empty recommendation grid when Heritage live catalog is not configured yet
- adds multi-unit installation support by evaluating packages of identical heaters in parallel
- adds delete support for saved heater quote runs so staff can remove bad or duplicate sizing attempts

Design notes:

- multi-unit installs are modeled as identical heaters working together in parallel
- candidate ranking compares the package BTU output against the original required BTU target
- the saved candidate keeps per-unit data in payload metadata while package totals are shown in the main fields
- the delete action removes the run, its candidate rows, and any `heater_quote` external links created from that run

This block intentionally avoids adding new DB columns so it can ride on top of the existing Block 2A schema without a migration.
