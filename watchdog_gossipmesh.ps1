# PowerShell Watchdog for GossipMesh daemon
# Bypass execution policy for this script
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force

$launchScript = "G:\My Drive\Devproxy\GossipMesh\launch-gossipmesh.ps1"

while ($true) {
    try {
        $running = Get-Process -Name pwsh -ErrorAction SilentlyContinue |
            Where-Object { $_.CommandLine -match [regex]::Escape($launchScript) }
    } catch {
        $running = $null
    }
    if (-not $running) {
        Write-Host "$(Get-Date) – GossipMesh daemon not running, starting it..."
        powershell -NoProfile -ExecutionPolicy Bypass -File $launchScript
    } else {
        Write-Host "$(Get-Date) – GossipMesh daemon is alive."
    }
    Start-Sleep -Seconds 30
}
