param(
    [string]$PlatformDir = "C:\Users\krist\Desktop\unified_pool_service_platform_build\unified_pool_service_platform_build"
)

$ErrorActionPreference = "Stop"

function Stop-Port {
    param([int]$Port)
    $conn = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($conn) {
        Write-Host "Stopping port $Port PID $($conn.OwningProcess)"
        Stop-Process -Id $conn.OwningProcess -Force
        Start-Sleep -Seconds 2
    }
}

function Run-Or-Throw {
    param(
        [Parameter(Mandatory=$true)][string]$FilePath,
        [Parameter(Mandatory=$false)][string[]]$ArgumentList = @()
    )
    & $FilePath @ArgumentList
    if ($LASTEXITCODE -ne 0) {
        throw ("Command failed with exit code {0}: {1} {2}" -f $LASTEXITCODE, $FilePath, ($ArgumentList -join ' '))
    }
}

if (!(Test-Path -LiteralPath $PlatformDir)) {
    throw "Platform folder not found: $PlatformDir"
}

Stop-Port 8010
Stop-Port 8501

Set-Location $PlatformDir

if (Test-Path -LiteralPath ".venv") {
    Write-Host "Removing broken platform .venv..."
    Remove-Item -LiteralPath ".venv" -Recurse -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 2
}

if (Test-Path -LiteralPath ".venv") {
    Write-Host "Retrying .venv removal..."
    Remove-Item -LiteralPath ".venv" -Recurse -Force -ErrorAction Stop
}

$pyver = $null
foreach ($v in @("-3.12", "-3.13", "-3")) {
    & py $v -V *> $null
    if ($LASTEXITCODE -eq 0) {
        $pyver = $v
        break
    }
}
if (-not $pyver) {
    throw "No usable Python 3 launcher found."
}

Write-Host "Creating .venv with py $pyver"
Run-Or-Throw -FilePath "py" -ArgumentList @($pyver, "-m", "venv", ".venv")

$Py = Join-Path $PlatformDir ".venv\Scripts\python.exe"
if (!(Test-Path -LiteralPath $Py)) {
    throw "Venv python was not created: $Py"
}

Run-Or-Throw -FilePath $Py -ArgumentList @("-V")
Run-Or-Throw -FilePath $Py -ArgumentList @("-m", "pip", "install", "--upgrade", "pip", "setuptools", "wheel")
& $Py -m pip cache purge | Out-Host

# First install the project requirements from scratch.
Run-Or-Throw -FilePath $Py -ArgumentList @("-m", "pip", "install", "--no-cache-dir", "--force-reinstall", "-r", "requirements.txt")

# Then force reinstall the compiled package that has repeatedly become corrupt/missing.
Run-Or-Throw -FilePath $Py -ArgumentList @("-m", "pip", "install", "--no-cache-dir", "--force-reinstall", "--only-binary=:all:", "pydantic-core")

# Hard import the compiled module, not just find_spec.
Run-Or-Throw -FilePath $Py -ArgumentList @("-c", "import pydantic_core._pydantic_core as core; print('pydantic_core binary import ok')")
Run-Or-Throw -FilePath $Py -ArgumentList @("-c", "import pydantic_core, pydantic, fastapi, sqlmodel, streamlit, httpx; print('pydantic_core:', pydantic_core.__version__); print('pydantic:', pydantic.__version__); print('fastapi:', fastapi.__version__); print('streamlit:', streamlit.__version__); print('httpx:', httpx.__version__)")
Run-Or-Throw -FilePath $Py -ArgumentList @("-c", "from app.api.main import app; print('platform API import ok')")

Write-Host "PASS | platform .venv repaired"
