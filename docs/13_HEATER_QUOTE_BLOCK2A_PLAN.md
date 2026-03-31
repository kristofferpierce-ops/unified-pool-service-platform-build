# Block 2A · Heater Quote Module

This block adds a modular heater quote tool to Repo B.

## Purpose

Give staff a safe local tool that can:
- size pool or spa heating demand
- recommend heater candidates in an ideal / viable / underpowered band
- show Heritage sourced pricing when a normalized Heritage catalog feed is available
- attach the chosen heater recommendation to an open quote case without bypassing the quote workflow ledger

## What is included

- Heritage connector scaffolding
- heater sizing service and local persistence tables
- heater quote API routes
- Streamlit page for heater sizing and candidate selection
- quote-case attachment through the existing external-link ledger
- test coverage for sizing, ranking, and attachment behavior

## What is deliberately conservative

This block does not assume private Heritage endpoint contracts that have not been documented publicly.
The connector supports:
- local fallback catalog via system settings
- optional normalized catalog URL
- optional local catalog JSON file

## Environment variables

Optional Heritage settings:

- `HERITAGE_ACCOUNT_ID`
- `HERITAGE_API_KEY`
- `HERITAGE_DEFAULT_BRANCH`
- `HERITAGE_CATALOG_URL`
- `HERITAGE_LOCAL_CATALOG_PATH`
- `HERITAGE_AUTH_MODE`

## UI notes

Every clickable element must keep hover help.
The Heater Quote page follows the same staff-friendly tooltip rule as the rest of the platform.

## Expected next step after Block 2A

Block 2B should generalize the same equipment-quote pattern for:
- pumps
- filters
- automation systems
- salt systems
- chillers
