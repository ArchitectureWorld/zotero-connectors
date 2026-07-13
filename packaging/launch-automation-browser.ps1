[CmdletBinding()]
param(
    [string]$InitialUrl = 'chrome://newtab/',
    [switch]$Minimized
)

$ErrorActionPreference = 'Stop'
$InstallDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$BrowserExe = Join-Path $InstallDir 'browser\chrome-win64\chrome.exe'
$ExtensionDir = Join-Path $InstallDir 'extension'
$ProfileDir = Join-Path $InstallDir 'browser-profile'
$LogDir = Join-Path $InstallDir 'logs'

if (-not (Test-Path -LiteralPath $BrowserExe)) {
    throw "没有找到自动化浏览器：$BrowserExe"
}
if (-not (Test-Path -LiteralPath (Join-Path $ExtensionDir 'manifest.json'))) {
    throw "没有找到 Zotero Connector 插件：$ExtensionDir"
}

New-Item -ItemType Directory -Path $ProfileDir -Force | Out-Null
New-Item -ItemType Directory -Path $LogDir -Force | Out-Null

$arguments = @(
    ('--user-data-dir="{0}"' -f $ProfileDir),
    ('--load-extension="{0}"' -f $ExtensionDir),
    '--no-first-run',
    '--no-default-browser-check',
    '--disable-search-engine-choice-screen',
    ('"{0}"' -f $InitialUrl)
) -join ' '

$startOptions = @{
    FilePath = $BrowserExe
    ArgumentList = $arguments
    WorkingDirectory = Split-Path -Parent $BrowserExe
}
if ($Minimized) {
    $startOptions.WindowStyle = 'Minimized'
}

$process = Start-Process @startOptions -PassThru

$state = @{
    browser_pid = $process.Id
    browser_exe = $BrowserExe
    extension_dir = $ExtensionDir
    profile_dir = $ProfileDir
    started_at = (Get-Date).ToString('o')
} | ConvertTo-Json
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText(
    (Join-Path $InstallDir 'browser-state.json'),
    $state,
    $utf8NoBom
)

Write-Output $process.Id
