[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidatePattern('^[a-p]{32}$')]
    [string]$ExtensionId,

    [ValidateSet('Chrome', 'Edge')]
    [string]$Browser = 'Chrome'
)

$ErrorActionPreference = 'Stop'
$HostName = 'org.zotero.script_trigger'
$RepoRoot = Split-Path -Parent $PSScriptRoot
$SourceDir = Join-Path $RepoRoot 'native-host'
$InstallDir = Join-Path $env:LOCALAPPDATA 'ZoteroScriptTrigger'
$BuildDir = Join-Path $InstallDir 'pyinstaller-build'
$SpecDir = Join-Path $InstallDir 'pyinstaller-spec'
$HostExe = Join-Path $InstallDir 'zotero_script_trigger_host.exe'
$HostManifest = Join-Path $InstallDir "$HostName.json"
$ConfigPath = Join-Path $InstallDir 'config.json'

function Resolve-Python {
    $py = Get-Command py -ErrorAction SilentlyContinue
    if ($py) {
        return @{ Exe = $py.Source; Prefix = @('-3') }
    }
    $python = Get-Command python -ErrorAction SilentlyContinue
    if ($python) {
        return @{ Exe = $python.Source; Prefix = @() }
    }
    throw 'Python 3 was not found. Install Python 3 and enable the py launcher or python command.'
}

function Invoke-Python([hashtable]$Python, [string[]]$Arguments) {
    & $Python.Exe @($Python.Prefix + $Arguments)
    if ($LASTEXITCODE -ne 0) {
        throw "Python command failed with exit code $LASTEXITCODE"
    }
}

function Write-Utf8NoBom([string]$Path, [string]$Content) {
    $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllText($Path, $Content, $utf8NoBom)
}

function Register-NativeHost([string]$RegistryPath) {
    New-Item -Path $RegistryPath -Force | Out-Null
    Set-Item -Path $RegistryPath -Value $HostManifest
}

New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null
Remove-Item -Recurse -Force $BuildDir, $SpecDir -ErrorAction SilentlyContinue

$Python = Resolve-Python
Invoke-Python $Python @('-m', 'pip', 'install', '--user', 'pyinstaller>=6,<7')
Invoke-Python $Python @(
    '-m', 'PyInstaller',
    '--noconfirm',
    '--clean',
    '--onefile',
    '--name', 'zotero_script_trigger_host',
    '--distpath', $InstallDir,
    '--workpath', $BuildDir,
    '--specpath', $SpecDir,
    '--paths', $SourceDir,
    (Join-Path $SourceDir 'zotero_script_trigger_host.py')
)

Copy-Item (Join-Path $SourceDir 'zotero_script_trigger_cli.py') $InstallDir -Force
Copy-Item (Join-Path $SourceDir 'host_config.py') $InstallDir -Force

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

if ($Browser -eq 'Chrome') {
    Register-NativeHost "HKCU:\Software\Google\Chrome\NativeMessagingHosts\$HostName"
}
if ($Browser -eq 'Edge') {
    Register-NativeHost "HKCU:\Software\Microsoft\Edge\NativeMessagingHosts\$HostName"
}

Remove-Item -Recurse -Force $BuildDir, $SpecDir -ErrorAction SilentlyContinue

Write-Host ''
Write-Host 'Zotero script trigger installed.' -ForegroundColor Green
Write-Host "Extension ID: $ExtensionId"
Write-Host "Native host: $HostExe"
Write-Host "Config: $ConfigPath"
Write-Host ''
Write-Host 'Reload the unpacked Zotero Connector extension, then test:'
Write-Host "py -3 `"$InstallDir\zotero_script_trigger_cli.py`" ping"
