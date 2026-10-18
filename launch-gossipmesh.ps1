$ErrorActionPreference = 'Continue'
Set-Location -Path "G:\My Drive\GossipMesh"

Write-Host "=================================================================" -ForegroundColor Cyan
Write-Host "      GOSSIPMESH AUTONOMOUS MULTI-AGENT ADVANCEMENT DAEMON       " -ForegroundColor Cyan
Write-Host "=================================================================" -ForegroundColor Cyan
Write-Host "[*] Repo: Aditya-9-6/GossipMesh" -ForegroundColor Green
Write-Host "[*] Attribution: Aditya Dahale <aditya-9-6@users.noreply.github.com>" -ForegroundColor Green

# Load Gemini API Key Pool from environment or local .gemini_keys
$keyFiles = @(
    "G:\My Drive\GossipMesh\.gemini_keys",
    "G:\My Drive\Devproxy\.gemini_keys",
    "$env:USERPROFILE\.gemini_keys"
)

$keys = @()
foreach ($kf in $keyFiles) {
    if (Test-Path $kf) {
        $lines = Get-Content $kf | Where-Object { $_.Trim() -ne '' -and -not $_.StartsWith('#') }
        foreach ($l in $lines) {
            $trimmed = $l.Trim()
            if ($trimmed -and -not ($keys -contains $trimmed)) {
                $keys += $trimmed
            }
        }
    }
}

if ($env:GEMINI_KEY_POOL) {
    $poolKeys = $env:GEMINI_KEY_POOL -split ','
    foreach ($k in $poolKeys) {
        $trimmed = $k.Trim()
        if ($trimmed -and -not ($keys -contains $trimmed)) {
            $keys += $trimmed
        }
    }
}

if ($keys.Count -gt 0) {
    $env:GEMINI_KEY_POOL = ($keys -join ',')
    $env:GEMINI_API_KEY = $keys[0]
    Write-Host "[*] Loaded $($keys.Count) Gemini API key(s) into active rotation pool." -ForegroundColor Yellow
} else {
    Write-Host "[!] No Gemini keys found in .gemini_keys. Relying on system environment." -ForegroundColor DarkYellow
}

$env:PYTHONUNBUFFERED = "1"
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONUTF8 = "1"

$py = "G:\My Drive\GossipMesh\.venv\Scripts\python.exe"
if (-not (Test-Path $py)) {
    $py = "python"
}

# Continuous Loop with automatic recovery
while ($true) {
    try {
        Write-Host "`n[*] Starting GossipMesh autonomous loop cycle..." -ForegroundColor Magenta
        & $py scripts/autonomous_loop.py --workspace . --interval 15
    } catch {
        Write-Host "[!] Loop exited with error: $_" -ForegroundColor Red
    }
    Write-Host "[*] Pausing 10s before restart..." -ForegroundColor Gray
    Start-Sleep -Seconds 10
}
