Set-Location -LiteralPath 'G:\My Drive\Devproxy\GossipMesh'
$env:PATH = "$env:PATH;C:\Program Files\GitHub CLI"
$prNumbers = gh pr list --state open --json number -q '.[].number'
foreach ($pr in $prNumbers) {
    Write-Host "Processing PR #$pr"
    $env:PR_NUMBER = $pr
    python scripts/reviewer_bot.py
}
