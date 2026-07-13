[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$PackageRoot = Split-Path -Parent $PSScriptRoot
$InstallDir = Join-Path $env:LOCALAPPDATA 'ZoteroScriptTrigger'
$SourceExtension = Join-Path $PackageRoot '浏览器插件'
$SourceBrowser = Join-Path $PackageRoot 'browser\chrome-win64'
$SourceLauncher = Join-Path $PSScriptRoot 'launch-automation-browser.ps1'
$InstalledExtension = Join-Path $InstallDir 'extension'
$InstalledBrowser = Join-Path $InstallDir 'browser\chrome-win64'
$InstalledLauncher = Join-Path $InstallDir 'launch-automation-browser.ps1'
$CliExe = Join-Path $InstallDir 'zotero_script_trigger_cli.exe'

function Assert-PackageFile([string]$Path, [string]$Message) {
    if (-not (Test-Path -LiteralPath $Path)) {
        throw $Message
    }
}

function Copy-DirectoryClean([string]$Source, [string]$Destination) {
    Remove-Item -LiteralPath $Destination -Recurse -Force -ErrorAction SilentlyContinue
    New-Item -ItemType Directory -Path $Destination -Force | Out-Null
    Copy-Item -Path (Join-Path $Source '*') -Destination $Destination -Recurse -Force
}

function New-LauncherShortcut([string]$ShortcutPath) {
    $shortcutDir = Split-Path -Parent $ShortcutPath
    New-Item -ItemType Directory -Path $shortcutDir -Force | Out-Null
    $shell = New-Object -ComObject WScript.Shell
    $shortcut = $shell.CreateShortcut($ShortcutPath)
    $shortcut.TargetPath = "$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe"
    $shortcut.Arguments = "-NoProfile -ExecutionPolicy Bypass -File `"$InstalledLauncher`""
    $shortcut.WorkingDirectory = $InstallDir
    $shortcut.IconLocation = "$(Join-Path $InstalledBrowser 'chrome.exe'),0"
    $shortcut.Description = '启动内置 Zotero Connector 的自动化浏览器'
    $shortcut.Save()
}

function Wait-ForProtocolV3([int]$TimeoutSeconds = 60) {
    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    $lastOutput = ''
    while ((Get-Date) -lt $deadline) {
        Start-Sleep -Milliseconds 750
        try {
            $lastOutput = (& $CliExe ping 2>&1 | Out-String).Trim()
            if ($LASTEXITCODE -ne 0 -or -not $lastOutput) {
                continue
            }
            $response = $lastOutput | ConvertFrom-Json
            $capabilities = @($response.capabilities)
            if (
                $response.success -and
                [int]$response.protocolVersion -ge 3 -and
                $capabilities -contains 'save-url' -and
                $capabilities -contains 'save-to-collection'
            ) {
                return $response
            }
        } catch {
            $lastOutput = $_.Exception.Message
        }
    }
    throw "自动化浏览器已经启动，但协议 V3 自检未通过。最后返回：$lastOutput"
}

Assert-PackageFile (Join-Path $SourceExtension 'manifest.json') '安装包缺少“浏览器插件”目录。'
Assert-PackageFile (Join-Path $SourceBrowser 'chrome.exe') '安装包缺少内置自动化浏览器。'
Assert-PackageFile $SourceLauncher '安装包缺少自动化浏览器启动脚本。'
Assert-PackageFile (Join-Path $PSScriptRoot 'install.ps1') '安装包缺少本地助手安装脚本。'

Write-Host ''
Write-Host '正在安装 Zotero 自动化组件……' -ForegroundColor Cyan

& (Join-Path $PSScriptRoot 'install.ps1')

Write-Host '正在复制浏览器插件……'
Copy-DirectoryClean $SourceExtension $InstalledExtension

Write-Host '正在复制专用自动化浏览器……'
Copy-DirectoryClean $SourceBrowser $InstalledBrowser
Copy-Item -LiteralPath $SourceLauncher -Destination $InstalledLauncher -Force

$desktop = [Environment]::GetFolderPath('Desktop')
$startMenu = Join-Path ([Environment]::GetFolderPath('StartMenu')) 'Programs\Zotero Script Trigger'
New-LauncherShortcut (Join-Path $desktop 'Zotero 自动化浏览器.lnk')
New-LauncherShortcut (Join-Path $startMenu 'Zotero 自动化浏览器.lnk')

Write-Host '正在启动自动化浏览器并执行协议自检……'
& $InstalledLauncher | Out-Null
$response = Wait-ForProtocolV3

$installationState = @{
    installed_at = (Get-Date).ToString('o')
    install_dir = $InstallDir
    protocol_version = [int]$response.protocolVersion
    capabilities = @($response.capabilities)
    extension_id = $response.extensionId
    extension_version = $response.extensionVersion
    deployment_mode = 'bundled-chrome-for-testing'
} | ConvertTo-Json -Depth 4
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText(
    (Join-Path $InstallDir 'installation-state.json'),
    $installationState,
    $utf8NoBom
)

Write-Host ''
Write-Host '一键部署完成。' -ForegroundColor Green
Write-Host "协议版本：V$($response.protocolVersion)"
Write-Host '指定集合归档：已启用'
Write-Host '桌面入口：Zotero 自动化浏览器'
Write-Host ''
