$ErrorActionPreference = 'Stop'
$HostName = 'org.zotero.script_trigger'
$InstallDir = Join-Path $env:LOCALAPPDATA 'ZoteroScriptTrigger'
$BrowserExe = Join-Path $InstallDir 'browser\chrome-win64\chrome.exe'

if (Test-Path -LiteralPath $BrowserExe) {
    $normalizedBrowserExe = [System.IO.Path]::GetFullPath($BrowserExe)
    $processes = @(Get-CimInstance Win32_Process -Filter "Name='chrome.exe'" -ErrorAction SilentlyContinue | Where-Object {
        $_.ExecutablePath -and
        [System.IO.Path]::GetFullPath($_.ExecutablePath) -eq $normalizedBrowserExe
    })
    foreach ($process in $processes) {
        & taskkill.exe /PID $process.ProcessId /T /F 2>$null | Out-Null
    }
}

Remove-Item "HKCU:\Software\Google\Chrome\NativeMessagingHosts\$HostName" -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item "HKCU:\Software\Microsoft\Edge\NativeMessagingHosts\$HostName" -Recurse -Force -ErrorAction SilentlyContinue

$desktopShortcut = Join-Path ([Environment]::GetFolderPath('Desktop')) 'Zotero 自动化浏览器.lnk'
$startMenuDir = Join-Path ([Environment]::GetFolderPath('StartMenu')) 'Programs\Zotero Script Trigger'
Remove-Item -LiteralPath $desktopShortcut -Force -ErrorAction SilentlyContinue
Remove-Item -LiteralPath $startMenuDir -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item -LiteralPath $InstallDir -Recurse -Force -ErrorAction SilentlyContinue

Write-Host ''
Write-Host 'Zotero 自动化组件已完整卸载。' -ForegroundColor Green
Write-Host ''
