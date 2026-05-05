param(
    [string]$RepoRoot = "",
    [ValidateSet("status", "audit", "launch", "stop", "all")]
    [string]$Action = "status"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Write-Section {
    param([string]$Title)
    Write-Host ""
    Write-Host "=============================================================================="
    Write-Host $Title
    Write-Host "=============================================================================="
}

function Resolve-KpsRepoRoot {
    param([string]$InputRepoRoot)

    if (-not [string]::IsNullOrWhiteSpace($InputRepoRoot)) {
        return (Resolve-Path -LiteralPath $InputRepoRoot).Path
    }

    $ScriptDir = Split-Path -Parent $PSCommandPath
    if ($ScriptDir -and (Split-Path -Leaf $ScriptDir) -eq "scripts") {
        return (Resolve-Path -LiteralPath (Split-Path -Parent $ScriptDir)).Path
    }

    $Current = (Get-Location).Path
    $Nested = Join-Path $Current "unified_pool_service_platform_build"
    if (Test-Path $Nested) {
        return (Resolve-Path -LiteralPath $Nested).Path
    }

    return (Resolve-Path -LiteralPath $Current).Path
}

function Get-KpsPython {
    param([string]$Repo)
    $VenvPython = Join-Path $Repo ".venv\Scripts\python.exe"
    if (Test-Path $VenvPython) {
        return $VenvPython
    }
    return "python"
}

function Invoke-Checked {
    param(
        [string]$Exe,
        [string[]]$CommandArgs
    )

    $Display = @($Exe) + @($CommandArgs)
    Write-Host ("RUN: {0}" -f ($Display -join " "))
    & $Exe @CommandArgs
    if ($LASTEXITCODE -ne 0) {
        throw ("{0} failed with exit code {1}" -f $Exe, $LASTEXITCODE)
    }
}

function Set-KpsSafeInspectionEnv {
    $env:LACRM_DEFAULT_MODE = "dry_run"
    $env:LACRM_LIVE_WRITE = "false"
    $env:LIVE_WRITE_DISABLED = "true"
    $env:LIVE_WRITE_UNARMED = "true"
    $env:NO_BRIDGE_POST = "true"
    $env:NO_NETWORK_TRANSPORT_IMPLEMENTATION = "true"
    $env:NO_NETWORK_SOCKETS = "true"
}

function Show-KpsSafeInspectionEnv {
    Write-Host "Safe local inspection environment:"
    Write-Host ("  LACRM_DEFAULT_MODE={0}" -f $env:LACRM_DEFAULT_MODE)
    Write-Host ("  LACRM_LIVE_WRITE={0}" -f $env:LACRM_LIVE_WRITE)
    Write-Host ("  LIVE_WRITE_DISABLED={0}" -f $env:LIVE_WRITE_DISABLED)
    Write-Host ("  LIVE_WRITE_UNARMED={0}" -f $env:LIVE_WRITE_UNARMED)
    Write-Host ("  NO_BRIDGE_POST={0}" -f $env:NO_BRIDGE_POST)
    Write-Host ("  NO_NETWORK_TRANSPORT_IMPLEMENTATION={0}" -f $env:NO_NETWORK_TRANSPORT_IMPLEMENTATION)
    Write-Host ("  NO_NETWORK_SOCKETS={0}" -f $env:NO_NETWORK_SOCKETS)
}

function Get-KpsPortProcess {
    param([int]$Port)
    $Conn = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
    if (-not $Conn) {
        return $null
    }
    $Proc = Get-CimInstance Win32_Process -Filter ("ProcessId={0}" -f $Conn.OwningProcess) -ErrorAction SilentlyContinue
    if (-not $Proc) {
        return [pscustomobject]@{
            Port = $Port
            ProcessId = $Conn.OwningProcess
            Name = "unknown"
            CommandLine = ""
        }
    }
    return [pscustomobject]@{
        Port = $Port
        ProcessId = $Proc.ProcessId
        Name = $Proc.Name
        CommandLine = [string]$Proc.CommandLine
    }
}

function Show-KpsPortStatus {
    foreach ($Port in @(8000, 8501, 8502, 4040)) {
        $Info = Get-KpsPortProcess -Port $Port
        if ($Info) {
            Write-Host ""
            Write-Host ("PORT {0} LISTENING" -f $Port)
            Write-Host ("  PID: {0}" -f $Info.ProcessId)
            Write-Host ("  Name: {0}" -f $Info.Name)
            Write-Host ("  CommandLine: {0}" -f $Info.CommandLine)
        } else {
            Write-Host ""
            Write-Host ("PORT {0} NOT LISTENING" -f $Port)
        }
    }
}

function Stop-KpsLocalAppListeners {
    param([string]$Repo)

    Write-Section "Stop existing KPS local app listeners"
    $Stopped = 0
    foreach ($Port in @(8000, 8501, 8502)) {
        $Info = Get-KpsPortProcess -Port $Port
        if (-not $Info) {
            Write-Host ("SKIP: port {0} not listening" -f $Port)
            continue
        }

        $CommandLine = [string]$Info.CommandLine
        $LooksLikeKps = $false
        if ($CommandLine -like ("*{0}*" -f $Repo)) { $LooksLikeKps = $true }
        if ($CommandLine -like "*app.api.main:app*") { $LooksLikeKps = $true }
        if ($CommandLine -like "*streamlit*") { $LooksLikeKps = $true }
        if ($CommandLine -like "*_KPS_TEMP_STREAMLIT_HOME_DO_NOT_COMMIT.py*") { $LooksLikeKps = $true }

        if (-not $LooksLikeKps) {
            Write-Host ("SKIP: port {0} is owned by PID {1}, but it does not look like this KPS app." -f $Port, $Info.ProcessId)
            continue
        }

        Write-Host ("STOP: port {0}, PID {1}" -f $Port, $Info.ProcessId)
        Stop-Process -Id ([int]$Info.ProcessId) -Force -ErrorAction SilentlyContinue
        $Stopped++
    }
    Write-Host ("STOP PASS: stopped {0} KPS local listener process(es)." -f $Stopped)
}

function Test-KpsVenvImports {
    param(
        [string]$Repo,
        [string]$Python
    )
    Write-Section "Venv import proof"
    Push-Location $Repo
    try {
        Invoke-Checked -Exe $Python -CommandArgs @(
            "-c",
            "import sys, importlib; print('SYS_EXECUTABLE=' + sys.executable); print('SYS_PREFIX=' + sys.prefix); print('BASE_PREFIX=' + sys.base_prefix); import streamlit; import uvicorn; m=importlib.import_module('app.api.main'); assert hasattr(m, 'app'); print('VENV IMPORT CHECK PASS')"
        )
    }
    finally {
        Pop-Location
    }
}

function Get-KpsWorkflowPages {
    param([string]$Repo)
    $PagesRoot = Join-Path $Repo "ui\pages"
    if (-not (Test-Path $PagesRoot)) {
        return @()
    }
    $Pattern = "Quote|Front|Bridge|LACRM|Ring|Customer|Property|Skimmer|Fresh|Heritage|Replaster|Tool|Apply|CRM|Routing|Review"
    return @(Get-ChildItem $PagesRoot -Filter "*.py" -File | Where-Object { $_.Name -match $Pattern } | Sort-Object Name)
}

function Invoke-KpsSelectedCompileAudit {
    param(
        [string]$Repo,
        [string]$Python
    )

    Write-Section "Selected UI/service compile audit"
    $Targets = New-Object System.Collections.Generic.List[string]

    foreach ($Page in (Get-KpsWorkflowPages -Repo $Repo)) {
        $Targets.Add($Page.FullName) | Out-Null
    }

    $ServiceCandidates = @(
        "app\services\tools.py",
        "app\services\replaster_quote.py",
        "app\api\main.py",
        "app\api\app.py"
    )
    foreach ($Rel in $ServiceCandidates) {
        $Path = Join-Path $Repo $Rel
        if (Test-Path $Path) {
            $Targets.Add($Path) | Out-Null
        }
    }

    $UniqueTargets = @($Targets | Sort-Object -Unique)
    if ($UniqueTargets.Count -eq 0) {
        Write-Host "No selected UI/service files found for compile audit."
        return @()
    }

    $Results = @()
    foreach ($Target in $UniqueTargets) {
        Write-Host ("COMPILE CHECK: {0}" -f $Target)
        & $Python -m py_compile $Target
        $ExitCode = $LASTEXITCODE
        $Status = if ($ExitCode -eq 0) { "pass" } else { "fail" }
        $Results += [pscustomobject]@{
            path = $Target
            status = $Status
            exit_code = $ExitCode
        }
        if ($ExitCode -ne 0) {
            Write-Host ("COMPILE FAIL: {0}" -f $Target)
        }
    }

    $Failures = @($Results | Where-Object { $_.status -ne "pass" })
    if ($Failures.Count -gt 0) {
        Write-Host ""
        Write-Host "COMPILE AUDIT FOUND FAILURES:"
        foreach ($Failure in $Failures) {
            Write-Host ("  {0}" -f $Failure.path)
        }
    } else {
        Write-Host "COMPILE AUDIT PASS: selected workflow pages and service modules compile."
    }

    return @($Results)
}

function Write-KpsAuditReport {
    param(
        [string]$Repo,
        [object[]]$CompileResults
    )

    Write-Section "Write local audit report"
    $Timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $ReportDir = Join-Path $Repo ("backups\ui_stabilization_pass1_{0}" -f $Timestamp)
    New-Item -ItemType Directory -Force -Path $ReportDir | Out-Null

    $PortResults = @()
    foreach ($Port in @(8000, 8501, 8502, 4040)) {
        $Info = Get-KpsPortProcess -Port $Port
        if ($Info) {
            $PortResults += $Info
        } else {
            $PortResults += [pscustomobject]@{ Port = $Port; ProcessId = $null; Name = "not_listening"; CommandLine = "" }
        }
    }

    $WorkflowPages = @(Get-KpsWorkflowPages -Repo $Repo | ForEach-Object { $_.Name })
    $Payload = [ordered]@{
        generated_at = (Get-Date).ToString("o")
        mode = "ui_stabilization_pass1"
        repo = $Repo
        safety = [ordered]@{
            lacrm_default_mode = $env:LACRM_DEFAULT_MODE
            lacrm_live_write = $env:LACRM_LIVE_WRITE
            live_write_disabled = $env:LIVE_WRITE_DISABLED
            live_write_unarmed = $env:LIVE_WRITE_UNARMED
            no_bridge_post = $env:NO_BRIDGE_POST
            no_network_transport_implementation = $env:NO_NETWORK_TRANSPORT_IMPLEMENTATION
            no_network_sockets = $env:NO_NETWORK_SOCKETS
        }
        ports = $PortResults
        workflow_page_count = $WorkflowPages.Count
        workflow_pages = $WorkflowPages
        compile_results = $CompileResults
    }

    $JsonPath = Join-Path $ReportDir "ui_stabilization_pass1_report.json"
    $MarkdownPath = Join-Path $ReportDir "ui_stabilization_pass1_report.md"

    $Payload | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $JsonPath -Encoding UTF8

    $PassCount = @($CompileResults | Where-Object { $_.status -eq "pass" }).Count
    $FailCount = @($CompileResults | Where-Object { $_.status -ne "pass" }).Count

    $Markdown = @()
    $Markdown += "# UI Stabilization Pass 1 Report"
    $Markdown += ""
    $Markdown += ("Generated: {0}" -f (Get-Date).ToString("s"))
    $Markdown += ""
    $Markdown += "## Safety posture"
    $Markdown += ""
    $Markdown += "- LACRM_DEFAULT_MODE=dry_run"
    $Markdown += "- LACRM_LIVE_WRITE=false"
    $Markdown += "- LIVE_WRITE_DISABLED=true"
    $Markdown += "- LIVE_WRITE_UNARMED=true"
    $Markdown += "- NO_BRIDGE_POST=true"
    $Markdown += "- NO_NETWORK_TRANSPORT_IMPLEMENTATION=true"
    $Markdown += "- NO_NETWORK_SOCKETS=true"
    $Markdown += ""
    $Markdown += "## Compile summary"
    $Markdown += ""
    $Markdown += ("- Pass: {0}" -f $PassCount)
    $Markdown += ("- Fail: {0}" -f $FailCount)
    $Markdown += ("- Workflow page candidates: {0}" -f $WorkflowPages.Count)
    if ($FailCount -gt 0) {
        $Markdown += ""
        $Markdown += "## Failures"
        $Markdown += ""
        foreach ($Failure in @($CompileResults | Where-Object { $_.status -ne "pass" })) {
            $Markdown += ("- {0}" -f $Failure.path)
        }
    }
    $Markdown += ""
    $Markdown += "## Next debugging target"
    $Markdown += ""
    $Markdown += "Use the Streamlit/backend windows to click the real workflow pages first: Tools, Quote Workflow, Heater Quote, Replaster Quote, Bridge Review, LACRM, RingCentral, Bridge/Routing pages."

    $Markdown -join "`r`n" | Set-Content -LiteralPath $MarkdownPath -Encoding UTF8

    Write-Host ("REPORT JSON: {0}" -f $JsonPath)
    Write-Host ("REPORT MD:   {0}" -f $MarkdownPath)
}

function New-KpsTempHome {
    param([string]$TempHome)
    $HomeSource = @'
import pathlib
import streamlit as st

st.set_page_config(
    page_title="KPS R&D UI Pages",
    layout="wide",
)

pages_dir = pathlib.Path(__file__).parent / "pages"
pages = sorted(p.name for p in pages_dir.glob("*.py"))

st.title("KPS R&D UI Pages Launcher")
st.caption("Use the Streamlit sidebar to open the phase/tool pages. This launcher is for local inspection only.")

st.write("Safety posture for this local inspection:")
st.code(
    "LACRM_DEFAULT_MODE=dry_run\n"
    "LACRM_LIVE_WRITE=false\n"
    "LIVE_WRITE_DISABLED=true\n"
    "LIVE_WRITE_UNARMED=true\n"
    "NO_BRIDGE_POST=true\n"
    "NO_NETWORK_TRANSPORT_IMPLEMENTATION=true\n"
    "NO_NETWORK_SOCKETS=true"
)

st.write(f"Detected {len(pages)} page files under ui/pages.")

workflow_keywords = (
    "Quote", "Front", "Bridge", "LACRM", "Ring", "Customer", "Property",
    "Skimmer", "Fresh", "Heritage", "Replaster", "Tool", "Apply", "CRM",
    "Routing", "Review",
)
workflow_pages = [p for p in pages if any(k in p for k in workflow_keywords)]

st.subheader("Likely real workflow pages")
st.write(f"Detected {len(workflow_pages)} workflow-like page files.")
with st.expander("Show likely workflow pages", expanded=False):
    for page in workflow_pages:
        st.write(page)

with st.expander("Show all detected page files", expanded=False):
    for page in pages:
        st.write(page)
'@
    Set-Content -LiteralPath $TempHome -Value $HomeSource -Encoding UTF8
}

function Start-KpsLocalProgram {
    param(
        [string]$Repo,
        [string]$Python
    )

    Write-Section "Launch KPS local backend and Streamlit UI"
    Set-KpsSafeInspectionEnv
    Show-KpsSafeInspectionEnv

    Stop-KpsLocalAppListeners -Repo $Repo
    Start-Sleep -Seconds 2

    $UiRoot = Join-Path $Repo "ui"
    $TempHome = Join-Path $UiRoot "_KPS_TEMP_STREAMLIT_HOME_DO_NOT_COMMIT.py"
    if (Test-Path $TempHome) {
        Remove-Item -LiteralPath $TempHome -Force
        Write-Host ("REMOVED stale temporary Streamlit home: {0}" -f $TempHome)
    }

    New-KpsTempHome -TempHome $TempHome
    Invoke-Checked -Exe $Python -CommandArgs @("-m", "py_compile", $TempHome)

    $BackendRunner = Join-Path $env:TEMP "RUN_KPS_BACKEND_UI_STABILIZATION_PASS1.ps1"
    $StreamlitRunner = Join-Path $env:TEMP "RUN_KPS_STREAMLIT_UI_STABILIZATION_PASS1.ps1"
    $BackendLog = Join-Path $env:TEMP "KPS_BACKEND_UI_STABILIZATION_PASS1_PROOF.log"
    $StreamlitLog = Join-Path $env:TEMP "KPS_STREAMLIT_UI_STABILIZATION_PASS1_PROOF.log"

    $BackendRunnerSource = @'
param(
    [Parameter(Mandatory=$true)][string]$Repo,
    [Parameter(Mandatory=$true)][string]$Python,
    [Parameter(Mandatory=$true)][string]$ProofLog
)

$ErrorActionPreference = "Continue"
Set-Location $Repo

$env:LACRM_DEFAULT_MODE = "dry_run"
$env:LACRM_LIVE_WRITE = "false"
$env:LIVE_WRITE_DISABLED = "true"
$env:LIVE_WRITE_UNARMED = "true"
$env:NO_BRIDGE_POST = "true"
$env:NO_NETWORK_TRANSPORT_IMPLEMENTATION = "true"
$env:NO_NETWORK_SOCKETS = "true"

Write-Host ""
Write-Host "=============================================================================="
Write-Host "KPS BACKEND/API - UI STABILIZATION PASS 1"
Write-Host "=============================================================================="
Write-Host "Repo:"
Write-Host "  $Repo"
Write-Host "Python:"
Write-Host "  $Python"
Write-Host "Backend URL:"
Write-Host "  http://127.0.0.1:8000"
Write-Host "FastAPI docs:"
Write-Host "  http://127.0.0.1:8000/docs"
Write-Host ""

& $Python -c "import sys; print('BACKEND_SYS_EXECUTABLE=' + sys.executable); print('BACKEND_SYS_PREFIX=' + sys.prefix); print('BACKEND_BASE_PREFIX=' + sys.base_prefix)" | Tee-Object -FilePath $ProofLog

Write-Host ""
Write-Host "Leave this window open while checking backend-dependent pages. Press CTRL+C to stop backend."
Write-Host ""
& $Python -m uvicorn app.api.main:app --host 127.0.0.1 --port 8000

Write-Host ""
Write-Host "Backend process ended."
Read-Host "Press Enter to close this backend window"
'@
    Set-Content -LiteralPath $BackendRunner -Value $BackendRunnerSource -Encoding UTF8

    $StreamlitRunnerSource = @'
param(
    [Parameter(Mandatory=$true)][string]$Repo,
    [Parameter(Mandatory=$true)][string]$Python,
    [Parameter(Mandatory=$true)][string]$TempHome,
    [Parameter(Mandatory=$true)][string]$ProofLog
)

$ErrorActionPreference = "Continue"
Set-Location $Repo

$env:LACRM_DEFAULT_MODE = "dry_run"
$env:LACRM_LIVE_WRITE = "false"
$env:LIVE_WRITE_DISABLED = "true"
$env:LIVE_WRITE_UNARMED = "true"
$env:NO_BRIDGE_POST = "true"
$env:NO_NETWORK_TRANSPORT_IMPLEMENTATION = "true"
$env:NO_NETWORK_SOCKETS = "true"

Write-Host ""
Write-Host "=============================================================================="
Write-Host "KPS STREAMLIT UI - UI STABILIZATION PASS 1"
Write-Host "=============================================================================="
Write-Host "Repo:"
Write-Host "  $Repo"
Write-Host "Python:"
Write-Host "  $Python"
Write-Host "Temporary Streamlit home:"
Write-Host "  $TempHome"
Write-Host "Streamlit URL:"
Write-Host "  http://127.0.0.1:8501"
Write-Host ""

& $Python -c "import sys; print('STREAMLIT_SYS_EXECUTABLE=' + sys.executable); print('STREAMLIT_SYS_PREFIX=' + sys.prefix); print('STREAMLIT_BASE_PREFIX=' + sys.base_prefix)" | Tee-Object -FilePath $ProofLog

Write-Host ""
Write-Host "Leave this window open while checking Streamlit pages. Press CTRL+C to stop Streamlit."
Write-Host ""
try {
    & $Python -m streamlit run $TempHome --server.address 127.0.0.1 --server.port 8501 --browser.gatherUsageStats false
}
finally {
    Write-Host ""
    Write-Host "Streamlit process ended."
    if (Test-Path $TempHome) {
        Remove-Item -LiteralPath $TempHome -Force
        Write-Host "REMOVED temporary Streamlit home:"
        Write-Host "  $TempHome"
    }
    Write-Host ""
    Read-Host "Press Enter to close this Streamlit window"
}
'@
    Set-Content -LiteralPath $StreamlitRunner -Value $StreamlitRunnerSource -Encoding UTF8

    Start-Process powershell.exe -ArgumentList @("-NoExit", "-ExecutionPolicy", "Bypass", "-File", $BackendRunner, "-Repo", $Repo, "-Python", $Python, "-ProofLog", $BackendLog)
    Start-Sleep -Seconds 5
    Start-Process powershell.exe -ArgumentList @("-NoExit", "-ExecutionPolicy", "Bypass", "-File", $StreamlitRunner, "-Repo", $Repo, "-Python", $Python, "-TempHome", $TempHome, "-ProofLog", $StreamlitLog)
    Start-Sleep -Seconds 7

    Start-Process "http://127.0.0.1:8000/docs"
    Start-Process "http://127.0.0.1:8501"

    Show-KpsPortStatus

    Write-Host ""
    Write-Host "Proof logs:"
    Write-Host ("  Backend:   {0}" -f $BackendLog)
    Write-Host ("  Streamlit: {0}" -f $StreamlitLog)
    Write-Host "LAUNCH PASS: backend and Streamlit launch commands were sent."
}

$Repo = Resolve-KpsRepoRoot -InputRepoRoot $RepoRoot
$Python = Get-KpsPython -Repo $Repo
$UiRoot = Join-Path $Repo "ui"
$PagesRoot = Join-Path $UiRoot "pages"

Write-Section "KPS UI Stabilization Pass 1 Launcher"
Write-Host ("Repo root: {0}" -f $Repo)
Write-Host ("Python: {0}" -f $Python)
Write-Host ("Action: {0}" -f $Action)
Write-Host "Mode: local inspection only / no staging / no commit / no live write"

if (-not (Test-Path $Repo)) { throw ("Repo not found: {0}" -f $Repo) }
if (-not (Test-Path $UiRoot)) { throw ("ui folder not found: {0}" -f $UiRoot) }
if (-not (Test-Path $PagesRoot)) { throw ("ui/pages folder not found: {0}" -f $PagesRoot) }
if (-not (Test-Path $Python) -and $Python -ne "python") { throw ("Python not found: {0}" -f $Python) }

Set-KpsSafeInspectionEnv

switch ($Action) {
    "status" {
        Write-Section "Status"
        Show-KpsSafeInspectionEnv
        Write-Host ""
        Write-Host "Git status check only:"
        & git -C $Repo status --short
        Show-KpsPortStatus
        $WorkflowPages = @(Get-KpsWorkflowPages -Repo $Repo)
        Write-Host ""
        Write-Host ("Workflow-like pages detected: {0}" -f $WorkflowPages.Count)
        $WorkflowPages | Select-Object -First 40 | ForEach-Object { Write-Host ("  {0}" -f $_.Name) }
    }
    "audit" {
        Test-KpsVenvImports -Repo $Repo -Python $Python
        $CompileResults = @(Invoke-KpsSelectedCompileAudit -Repo $Repo -Python $Python)
        Write-KpsAuditReport -Repo $Repo -CompileResults $CompileResults
    }
    "launch" {
        Test-KpsVenvImports -Repo $Repo -Python $Python
        Start-KpsLocalProgram -Repo $Repo -Python $Python
    }
    "stop" {
        Stop-KpsLocalAppListeners -Repo $Repo
        Show-KpsPortStatus
    }
    "all" {
        Write-Section "Status before audit"
        Show-KpsSafeInspectionEnv
        & git -C $Repo status --short
        Show-KpsPortStatus
        Test-KpsVenvImports -Repo $Repo -Python $Python
        $CompileResults = @(Invoke-KpsSelectedCompileAudit -Repo $Repo -Python $Python)
        Write-KpsAuditReport -Repo $Repo -CompileResults $CompileResults
        Write-Host "ALL PASS: status and audit completed. No servers launched by -Action all."
    }
}

