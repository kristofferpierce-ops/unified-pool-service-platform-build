# KPS UI Stabilization Pass 1

This pass adds a persistent local launcher and diagnostic surface for UI debugging before Phase 34.

## Why this exists

The recent local launch diagnostics showed that the correct local inspection topology is:

- FastAPI backend on `127.0.0.1:8000`
- Streamlit multipage UI on `127.0.0.1:8501`
- no ngrok tunnel unless explicitly needed
- repo `.venv` confirmed through `sys.executable` and `sys.prefix`

This pass turns the working ad-hoc launcher into a committed script so future UI debugging does not depend on fragile pasted shell blocks.

## Safety posture

The launcher always sets:

```text
LACRM_DEFAULT_MODE=dry_run
LACRM_LIVE_WRITE=false
LIVE_WRITE_DISABLED=true
LIVE_WRITE_UNARMED=true
NO_BRIDGE_POST=true
NO_NETWORK_TRANSPORT_IMPLEMENTATION=true
NO_NETWORK_SOCKETS=true
```

The patch does not enable live writes, bridge POSTs, network transport implementation, sockets, or external webhooks.

## Files added

```text
scripts/kps_ui_stabilization_pass1_launcher.ps1
ui/pages/000_KPS_UI_Stabilization_Pass1.py
docs/KPS_UI_STABILIZATION_PASS1.md
tests/test_kps_ui_stabilization_pass1.py
```

## Usage

From the parent workspace:

```powershell
$Parent = "C:\Users\krist\Desktop\unified_pool_service_platform_build"
$Repo = Join-Path $Parent "unified_pool_service_platform_build"
Set-Location $Parent

powershell.exe -NoProfile -ExecutionPolicy Bypass `
  -File (Join-Path $Repo "scripts\kps_ui_stabilization_pass1_launcher.ps1") `
  -RepoRoot $Repo `
  -Action status
```

To run the audit without launching servers:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass `
  -File (Join-Path $Repo "scripts\kps_ui_stabilization_pass1_launcher.ps1") `
  -RepoRoot $Repo `
  -Action audit
```

To launch local inspection windows:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass `
  -File (Join-Path $Repo "scripts\kps_ui_stabilization_pass1_launcher.ps1") `
  -RepoRoot $Repo `
  -Action launch
```

Expected listeners after launch:

```text
127.0.0.1:8000 = backend/API
127.0.0.1:8501 = Streamlit UI
127.0.0.1:4040 = not listening unless ngrok is intentionally launched
```

## Debugging priority

Debug real workflow pages first, not generated phase packet pages:

```text
9_Tools.py
11_Quote_Workflow.py
12_Heater_Quote.py
13_Replaster_Quote.py
14_Bridge_Review.py
Bridge / LACRM / RingCentral pages
```

The audit action writes local reports under `backups/ui_stabilization_pass1_*`. Those reports are intentionally not staged by the installer.

