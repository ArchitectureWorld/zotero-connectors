$ErrorActionPreference = 'Stop'
$Cli = Join-Path $env:LOCALAPPDATA 'ZoteroScriptTrigger\zotero_script_trigger_cli.exe'
if (-not (Test-Path $Cli)) {
    Write-Host '尚未安装本地助手。请先双击 1-安装本地助手.bat。' -ForegroundColor Red
    exit 1
}

$output = & $Cli ping 2>&1 | Out-String
$exitCode = $LASTEXITCODE
if ($exitCode -eq 0) {
    Write-Host ''
    Write-Host '连接成功：浏览器插件已经可以接收外部脚本命令。' -ForegroundColor Green
    Write-Host ''
    exit 0
}

Write-Host ''
Write-Host '连接失败。请确认：' -ForegroundColor Red
Write-Host '1. Chrome 已经打开；'
Write-Host '2. 已经按照第 2 步加载“浏览器插件”文件夹；'
Write-Host '3. 扩展管理页面中 Zotero Connector 处于启用状态。'
Write-Host ''
Write-Host $output
exit $exitCode
