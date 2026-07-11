$ErrorActionPreference = 'Stop'
$PackageRoot = Split-Path -Parent $PSScriptRoot
$ExtensionDir = Join-Path $PackageRoot '浏览器插件'

if (-not (Test-Path (Join-Path $ExtensionDir 'manifest.json'))) {
    throw '没有找到“浏览器插件”文件夹，请重新解压完整的 ZIP。'
}

Set-Clipboard -Value $ExtensionDir
Start-Process explorer.exe -ArgumentList ('"{0}"' -f $ExtensionDir)

$candidates = @(
    (Join-Path $env:ProgramFiles 'Google\Chrome\Application\chrome.exe'),
    (Join-Path ${env:ProgramFiles(x86)} 'Google\Chrome\Application\chrome.exe'),
    (Join-Path $env:LOCALAPPDATA 'Google\Chrome\Application\chrome.exe')
) | Where-Object { $_ -and (Test-Path $_) }

if ($candidates.Count -gt 0) {
    Start-Process -FilePath $candidates[0] -ArgumentList 'chrome://extensions/'
} else {
    Start-Process 'chrome://extensions/'
}

Write-Host ''
Write-Host '浏览器插件文件夹已经打开，文件夹路径也已复制。' -ForegroundColor Green
Write-Host '请在 Chrome 扩展页面完成三步：'
Write-Host '1. 打开右上角“开发者模式”；'
Write-Host '2. 点击“加载已解压的扩展程序”；'
Write-Host '3. 选择刚刚打开的“浏览器插件”文件夹。'
Write-Host ''
