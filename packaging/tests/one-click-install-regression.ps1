$ErrorActionPreference = 'Stop'

$packagingRoot = Split-Path -Parent $PSScriptRoot
$oneClickBat = Get-ChildItem -LiteralPath $packagingRoot -Filter '0-*.bat' | Select-Object -First 1
$installAll = Join-Path $packagingRoot 'install-all.ps1'
$launcher = Join-Path $packagingRoot 'launch-automation-browser.ps1'

if (-not $oneClickBat) {
    throw 'Missing one-click deployment BAT entrypoint.'
}
foreach ($path in @($installAll, $launcher)) {
    if (-not (Test-Path -LiteralPath $path)) {
        throw "Missing one-click deployment file: $path"
    }
}

$batText = [System.IO.File]::ReadAllText($oneClickBat.FullName, [System.Text.Encoding]::UTF8)
if ($batText -notmatch 'install-all\.ps1') {
    throw 'The one-click BAT must invoke install-all.ps1.'
}

$installText = [System.IO.File]::ReadAllText($installAll, [System.Text.Encoding]::UTF8)
foreach ($required in @(
    'install.ps1',
    'SourceExtension',
    'SourceBrowser',
    'chrome-win64',
    'launch-automation-browser.ps1',
    'save-to-collection',
    'protocolVersion',
    'Desktop',
    'StartMenu'
)) {
    if ($installText -notmatch [regex]::Escape($required)) {
        throw "install-all.ps1 is missing required deployment behavior: $required"
    }
}

$launcherText = [System.IO.File]::ReadAllText($launcher, [System.Text.Encoding]::UTF8)
foreach ($required in @('--user-data-dir', '--load-extension', 'chrome.exe')) {
    if ($launcherText -notmatch [regex]::Escape($required)) {
        throw "launch-automation-browser.ps1 is missing required browser argument: $required"
    }
}

Write-Host 'One-click deployment regression test passed.' -ForegroundColor Green
