[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$HostName = 'org.zotero.script_trigger'
$ExtensionId = 'anakemdifclhajhpbjlgfpeokaphddam'
$PackageRoot = Split-Path -Parent $PSScriptRoot
$AppDir = Join-Path $PackageRoot 'app'
$InstallDir = Join-Path $env:LOCALAPPDATA 'ZoteroScriptTrigger'
$HostExe = Join-Path $InstallDir 'zotero_script_trigger_host.exe'
$CliExe = Join-Path $InstallDir 'zotero_script_trigger_cli.exe'
$HostManifest = Join-Path $InstallDir "$HostName.json"
$ConfigPath = Join-Path $InstallDir 'config.json'

function Write-Utf8NoBom([string]$Path, [string]$Content) {
    $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllText($Path, $Content, $utf8NoBom)
}

function Register-NativeHost([string]$RegistryPath) {
    New-Item -Path $RegistryPath -Force | Out-Null
    Set-Item -Path $RegistryPath -Value $HostManifest
}

$SourceHost = Join-Path $AppDir 'zotero_script_trigger_host.exe'
$SourceCli = Join-Path $AppDir 'zotero_script_trigger_cli.exe'
if (-not (Test-Path $SourceHost) -or -not (Test-Path $SourceCli)) {
    throw '安装包文件不完整，请重新解压完整的 ZIP 后再运行。'
}

New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null
Copy-Item $SourceHost $HostExe -Force
Copy-Item $SourceCli $CliExe -Force

$randomBytes = New-Object byte[] 32
$rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
try { $rng.GetBytes($randomBytes) } finally { $rng.Dispose() }
$authKey = [Convert]::ToBase64String($randomBytes)

$sha = [System.Security.Cryptography.SHA256]::Create()
try {
    $userBytes = [System.Text.Encoding]::UTF8.GetBytes("$env:USERDOMAIN\$env:USERNAME")
    $hash = $sha.ComputeHash($userBytes)
} finally {
    $sha.Dispose()
}
$suffix = -join ($hash[0..7] | ForEach-Object { $_.ToString('x2') })
$pipeName = "\\.\pipe\zotero-script-trigger-$suffix"

$configJson = @{
    pipe_name = $pipeName
    authkey = $authKey
} | ConvertTo-Json
Write-Utf8NoBom $ConfigPath $configJson

$manifestJson = @{
    name = $HostName
    description = 'Zotero Connector external script trigger'
    path = $HostExe
    type = 'stdio'
    allowed_origins = @("chrome-extension://$ExtensionId/")
} | ConvertTo-Json -Depth 4
Write-Utf8NoBom $HostManifest $manifestJson

Register-NativeHost "HKCU:\Software\Google\Chrome\NativeMessagingHosts\$HostName"
Register-NativeHost "HKCU:\Software\Microsoft\Edge\NativeMessagingHosts\$HostName"

Write-Host ''
Write-Host '本地助手安装完成。' -ForegroundColor Green
Write-Host '接下来请运行：2-加载浏览器插件.bat'
Write-Host ''
