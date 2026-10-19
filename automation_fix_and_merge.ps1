# Automation script to fix CI and auto‑merge PRs in GossipMesh repository

# Get list of open PRs with relevant fields
$prJson = gh pr list --json number,headRefName,mergeable,state,title,author --limit 200
$prs = $prJson | ConvertFrom-Json

Write-Host "Found $($prs.Count) open PRs. Triggering CI fixer..."

foreach ($pr in $prs) {
    # Trigger the AI CI Fixer workflow for each PR
    Write-Host "Trigger CI fixer for PR #$($pr.number) ($($pr.title))"
    gh workflow run ai-ci-fixer.yml -f pr_number=$($pr.number) --ref main | Out-Null
}

# Simple wait to allow CI fixer runs to start. Adjust as needed.
Write-Host "Waiting 90 seconds for CI fixer runs to complete..."
Start-Sleep -Seconds 90

Write-Host "Triggering auto‑merge for MERGEABLE PRs..."
foreach ($pr in $prs) {
    if ($pr.mergeable -eq "MERGEABLE") {
        Write-Host "Auto‑merge PR #$($pr.number) ($($pr.title))"
        gh workflow run auto-merge-pr.yml -f pr_number=$($pr.number) --ref main | Out-Null
    } else {
        Write-Host "Skipping PR #$($pr.number) – mergeable status: $($pr.mergeable)"
    }
}

# Wait a short period for auto‑merge workflow to finish
Write-Host "Waiting 60 seconds for auto‑merge to settle..."
Start-Sleep -Seconds 60

# Generate a concise report
$reportPath = "automation_report.md"
"## Automation Report - $(Get-Date)" | Set-Content $reportPath
"" | Add-Content $reportPath

foreach ($pr in $prs) {
    $details = gh pr view $pr.number --json number,title,headRefName,baseRefName,mergeable,state,mergedAt,closedAt,updatedAt -q .
    $detailsObj = $details | ConvertFrom-Json
    $status = if ($detailsObj.mergedAt) { "MERGED" } elseif ($detailsObj.state -eq "CLOSED") { "CLOSED" } else { "OPEN" }
    "- PR #$($detailsObj.number): $($detailsObj.title)`n  - Head: $($detailsObj.headRefName) → Base: $($detailsObj.baseRefName)`n  - Mergeable: $($detailsObj.mergeable)`n  - Final status: $status`n  - Updated: $($detailsObj.updatedAt)" | Add-Content $reportPath
}

Write-Host "Automation report written to $reportPath"
