[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$HostName = 'org.zotero.script_trigger'
$InstallDir = Join-Path $env:LOCALAPPDATA 'ZoteroScriptTrigger'
$RegistryPaths = @(
    "HKCU:\Software\Google\Chrome\NativeMessagingHosts\$HostName",
    "HKCU:\Software\Microsoft\Edge\NativeMessagingHosts\$HostName"
)

foreach ($path in $RegistryPaths) {
    Remove-Item -Path $path -Recurse -Force -ErrorAction SilentlyContinue
}
Remove-Item -Path $InstallDir -Recurse -Force -ErrorAction SilentlyContinue
Write-Host 'Zotero script trigger uninstalled.' -ForegroundColor Green
