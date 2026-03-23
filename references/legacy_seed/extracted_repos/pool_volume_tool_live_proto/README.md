# Pool Volume Tool Live Prototype

This version upgrades the original mock-only prototype with a real address workflow.

## What is live now

- U.S. Census geocoder for address to coordinate lookup
- Florida statewide cadastral polygon service for parcel geometry and parcel metadata
- USGS NAIP aerial imagery export for live overhead imagery
- Basic computer-vision style pool detection inside the parcel boundary
- Monroe County permit search links generated when the address geocodes into Monroe County

## What is still not fully automated

- Permit parsing is not automatic yet
- Permit plans are not downloaded or OCR parsed yet
- Depth is still estimated unless permit data is provided manually

## Endpoints

### GET `/tools/pool-volume/health`
Returns service status.

### POST `/tools/pool-volume/inspect-live`
Returns raw live lookup data before gallon estimation.

### POST `/tools/pool-volume/estimate`
Runs the live lookup when `use_live_sources` is true and no explicit permit or imagery data was supplied.

## Example live request

```json
{
  "address": "1100 Simonton Street, Key West, FL 33040",
  "use_live_sources": true,
  "manual_overrides": {
    "property_type": "commercial"
  }
}
```

## Important accuracy note

Aerial imagery can estimate surface area, but gallons still depend heavily on average depth. Without permit dimensions or manual depth input, the result should be treated as a low-confidence estimate.

## Install and run

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -c "import uvicorn; uvicorn.run('main_example:app', host='127.0.0.1', port=8000, reload=True)"
```

Then open:

```text
http://127.0.0.1:8000/docs
```
