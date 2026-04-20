param(
    [string]$Workspace = "C:\Users\krist\Desktop\unified_pool_service_platform_build",
    [switch]$SkipRepair
)

$ErrorActionPreference = "Stop"

$PlatformDir = Join-Path $Workspace "unified_pool_service_platform_build"
$BridgeDir = Join-Path $Workspace "front_desk_bridge"

function Test-Port {
    param([int]$Port)
    try {
        $null -ne (Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction Stop | Select-Object -First 1)
    } catch {
        $false
    }
}

function Temp-Script {
    param([string]$Name, [string]$Body)
    $path = Join-Path $env:TEMP $Name
    Set-Content -LiteralPath $path -Value $Body -Encoding UTF8
    return $path
}

function Run-Or-Throw {
    param(
        [Parameter(Mandatory=$true)][string]$FilePath,
        [Parameter(Mandatory=$false)][string[]]$ArgumentList = @(),
        [Parameter(Mandatory=$false)][string]$WorkingDirectory = $PWD.Path
    )

    Push-Location $WorkingDirectory
    try {
        & $FilePath @ArgumentList
        if ($LASTEXITCODE -ne 0) {
            throw ("Command failed with exit code {0}: {1} {2}" -f $LASTEXITCODE, $FilePath, ($ArgumentList -join ' '))
        }
    }
    finally {
        Pop-Location
    }
}

if (!(Test-Path -LiteralPath $PlatformDir)) { throw "Platform folder not found: $PlatformDir" }
if (!(Test-Path -LiteralPath $BridgeDir)) { throw "Bridge folder not found: $BridgeDir" }

$RepairScript = Join-Path $PlatformDir "scripts\phase19_repair_platform_venv.ps1"
if (!(Test-Path -LiteralPath $RepairScript)) {
    throw "Repair script missing: $RepairScript"
}

if (-not $SkipRepair) {
    Write-Host "Running repair-first platform venv check..."
    Push-Location $PlatformDir
    try {
        & powershell -ExecutionPolicy Bypass -File $RepairScript -PlatformDir $PlatformDir
        if ($LASTEXITCODE -ne 0) {
            throw "Platform venv repair failed."
        }
    }
    finally {
        Pop-Location
    }
} else {
    Write-Host "Skipping repair because -SkipRepair was supplied."
}

$Py = Join-Path $PlatformDir ".venv\Scripts\python.exe"
if (!(Test-Path -LiteralPath $Py)) {
    throw "Platform venv python missing after repair: $Py"
}

# Critical: make sure the local app package is importable even if this script
# is launched from Downloads or another working directory.
$env:PYTHONPATH = $PlatformDir

Run-Or-Throw -FilePath $Py -ArgumentList @("-c", "import os, sys; print('cwd:', os.getcwd()); print('PYTHONPATH:', os.environ.get('PYTHONPATH')); import pydantic_core._pydantic_core; import httpx; from app.api.main import app; print('platform pre-start import ok')") -WorkingDirectory $PlatformDir

if (-not (Test-Port 8010)) {
    $api = Temp-Script "phase19_start_fastapi.ps1" @"
`$ErrorActionPreference = "Stop"
Set-Location "$PlatformDir"
`$env:PYTHONPATH = "$PlatformDir"
& "$Py" -m uvicorn app.api.main:app --host 127.0.0.1 --port 8010
"@
    Start-Process powershell -ArgumentList @("-NoExit", "-ExecutionPolicy", "Bypass", "-File", $api) | Out-Null
    Write-Host "Started FastAPI on 8010."
} else {
    Write-Host "FastAPI already running on 8010."
}

Start-Sleep -Seconds 2

if (-not (Test-Port 8501)) {
    $st = Temp-Script "phase19_start_streamlit.ps1" @"
`$ErrorActionPreference = "Stop"
Set-Location "$PlatformDir"
`$env:PYTHONPATH = "$PlatformDir"
& "$Py" -m streamlit run ui\Dashboard.py --server.port 8501
"@
    Start-Process powershell -ArgumentList @("-NoExit", "-ExecutionPolicy", "Bypass", "-File", $st) | Out-Null
    Write-Host "Started Streamlit on 8501."
} else {
    Write-Host "Streamlit already running on 8501."
}

Start-Sleep -Seconds 2

if (-not (Test-Port 8000)) {
    $br = Temp-Script "phase19_start_bridge.ps1" @"
`$ErrorActionPreference = "Stop"
Set-Location "$BridgeDir"
if (!(Test-Path ".venv\Scripts\python.exe")) {
    py -3 -m venv .venv
    & ".\.venv\Scripts\python.exe" -m pip install -r requirements.txt
}
& ".\.venv\Scripts\python.exe" main.py
"@
    Start-Process powershell -ArgumentList @("-NoExit", "-ExecutionPolicy", "Bypass", "-File", $br) | Out-Null
    Write-Host "Started bridge on 8000."
} else {
    Write-Host "Bridge already running on 8000."
}

Write-Host ""
Write-Host "URLs:"
Write-Host "  Streamlit: http://127.0.0.1:8501"
Write-Host "  FastAPI:   http://127.0.0.1:8010"
Write-Host "  Bridge:    http://127.0.0.1:8000"
