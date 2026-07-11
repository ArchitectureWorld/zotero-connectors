$ErrorActionPreference = 'Stop'

$scriptPath = Join-Path (Split-Path -Parent $PSScriptRoot) 'open-extension-page.ps1'
$tokens = $null
$parseErrors = $null
$ast = [System.Management.Automation.Language.Parser]::ParseFile(
    $scriptPath,
    [ref]$tokens,
    [ref]$parseErrors
)

if ($parseErrors.Count -gt 0) {
    $messages = ($parseErrors | ForEach-Object { $_.Message }) -join '; '
    throw "PowerShell parse failed: $messages"
}

# In Windows PowerShell, a pipeline with one result can become a scalar string.
# Indexing that scalar returns only its first character instead of the full path.
$unsafeIndexes = $ast.FindAll({
    param($node)
    if ($node -isnot [System.Management.Automation.Language.IndexExpressionAst]) {
        return $false
    }
    $target = $node.Target
    return (
        $target -is [System.Management.Automation.Language.VariableExpressionAst] -and
        $target.VariablePath.UserPath -eq 'candidates'
    )
}, $true)

if ($unsafeIndexes.Count -gt 0) {
    throw 'Regression: open-extension-page.ps1 indexes a possibly scalar candidates value.'
}

$firstPathSelectors = $ast.FindAll({
    param($node)
    return (
        $node -is [System.Management.Automation.Language.CommandAst] -and
        $node.GetCommandName() -eq 'Select-Object' -and
        $node.Extent.Text -match '-First\s+1'
    )
}, $true)

if ($firstPathSelectors.Count -eq 0) {
    throw 'Regression: open-extension-page.ps1 must select the first complete path with Select-Object -First 1.'
}

Write-Host 'Chrome path selection regression test passed.' -ForegroundColor Green
