$ErrorActionPreference = 'Stop'

$packagingRoot = Split-Path -Parent $PSScriptRoot
$oneClickBat = Join-Path $packagingRoot '0-一键安装并启动.bat'
$installAll = Join-Path $packagingRoot 'install-all.ps1'
$launcher = Join-Path $packagingRoot 'launch-automation-browser.ps1'

foreach ($path in @($oneClickBat, $installAll, $launcher)) {
    if (-not (Test-Path -LiteralPath $path)) {
        throw "Missing one-click deployment file: $path"
    }
}

$batText = [System.IO.File]::ReadAllText($oneClickBat, [System.Text.Encoding]::UTF8)
if ($batText -notmatch 'install-all\.ps1') {
    throw 'The one-click BAT must invoke install-all.ps1.'
}

$installText = [System.IO.File]::ReadAllText($installAll, [System.Text.Encoding]::UTF8)
foreach ($required in @(
    'install.ps1',
    '浏览器插件',
    'browser',
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
