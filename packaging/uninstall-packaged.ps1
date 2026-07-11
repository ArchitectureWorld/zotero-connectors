$ErrorActionPreference = 'Stop'
$HostName = 'org.zotero.script_trigger'
$InstallDir = Join-Path $env:LOCALAPPDATA 'ZoteroScriptTrigger'

Remove-Item "HKCU:\Software\Google\Chrome\NativeMessagingHosts\$HostName" -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item "HKCU:\Software\Microsoft\Edge\NativeMessagingHosts\$HostName" -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item $InstallDir -Recurse -Force -ErrorAction SilentlyContinue

Write-Host ''
Write-Host '本地助手已卸载。' -ForegroundColor Green
Write-Host '浏览器插件仍需在扩展管理页面中手动删除。'
Write-Host ''
