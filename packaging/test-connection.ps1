$ErrorActionPreference = 'Stop'
$Cli = Join-Path $env:LOCALAPPDATA 'ZoteroScriptTrigger\zotero_script_trigger_cli.exe'
if (-not (Test-Path $Cli)) {
    Write-Host '尚未安装本地助手。请先双击 1-安装本地助手.bat。' -ForegroundColor Red
    exit 1
}

$output = & $Cli ping 2>&1 | Out-String
$exitCode = $LASTEXITCODE
if ($exitCode -ne 0) {
    Write-Host ''
    Write-Host '连接失败。请确认：' -ForegroundColor Red
    Write-Host '1. Chrome 已经打开；'
    Write-Host '2. 已经按照第 2 步加载“浏览器插件”文件夹；'
    Write-Host '3. 扩展管理页面中 Zotero Connector 处于启用状态。'
    Write-Host ''
    Write-Host $output
    exit $exitCode
}

try {
    $response = $output | ConvertFrom-Json
} catch {
    Write-Host ''
    Write-Host '连接程序返回了无法识别的内容，请重新安装当前测试包。' -ForegroundColor Red
    Write-Host $output
    exit 1
}

$capabilities = @($response.capabilities)
if (-not $response.success -or [int]$response.protocolVersion -lt 2 -or $capabilities -notcontains 'save-url') {
    Write-Host ''
    Write-Host '检测到旧版插件。请删除旧插件，并重新加载当前包中的“浏览器插件”文件夹。' -ForegroundColor Red
    Write-Host "当前协议版本：$($response.protocolVersion)"
    Write-Host "当前功能：$($capabilities -join ', ')"
    exit 1
}

Write-Host ''
Write-Host '连接成功：浏览器插件已支持精确网页保存（协议 V2）。' -ForegroundColor Green
Write-Host "扩展版本：$($response.extensionVersion)"
Write-Host ''
exit 0
