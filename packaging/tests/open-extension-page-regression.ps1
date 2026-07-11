$ErrorActionPreference = 'Stop'

$scriptPath = Join-Path (Split-Path -Parent $PSScriptRoot) 'open-extension-page.ps1'
$content = Get-Content -LiteralPath $scriptPath -Raw

# In Windows PowerShell, a pipeline with one result can become a scalar string.
# Indexing that string with [0] returns only its first character (for example, "C").
if ($content -match '\$candidates\s*\[\s*0\s*\]') {
    throw 'Regression: open-extension-page.ps1 indexes a possibly scalar string with $candidates[0].'
}

if ($content -notmatch 'Select-Object\s+-First\s+1') {
    throw 'Regression: open-extension-page.ps1 must select the first complete path with Select-Object -First 1.'
}

Write-Host 'Chrome path selection regression test passed.' -ForegroundColor Green
