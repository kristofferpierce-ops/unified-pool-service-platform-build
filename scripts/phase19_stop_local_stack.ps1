param([int[]]$Ports = @(8010,8501,8000))
$ErrorActionPreference = "Stop"
foreach ($Port in $Ports) {
    $conn = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($conn) {
        $proc = Get-CimInstance Win32_Process -Filter "ProcessId=$($conn.OwningProcess)"
        Write-Host "Stopping port $Port PID $($conn.OwningProcess)"
        Write-Host $proc.CommandLine
        Stop-Process -Id $conn.OwningProcess -Force
    } else {
        Write-Host "Nothing listening on port $Port"
    }
}
