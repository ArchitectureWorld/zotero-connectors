$ErrorActionPreference = 'Stop'
$Cli = Join-Path $env:LOCALAPPDATA 'ZoteroScriptTrigger\zotero_script_trigger_cli.exe'
if (-not (Test-Path $Cli)) {
    Write-Host '尚未安装本地助手。请先双击 1-安装本地助手.bat。' -ForegroundColor Red
    exit 1
}

$output = & $Cli save-active 2>&1 | Out-String
$exitCode = $LASTEXITCODE
if ($exitCode -eq 0) {
    try {
        $result = $output | ConvertFrom-Json
        Write-Host ''
        Write-Host '保存命令已发送给 Zotero Connector。' -ForegroundColor Green
        if ($result.title) { Write-Host "网页：$($result.title)" }
        Write-Host '请到 Zotero 中确认文献是否已经出现。'
        Write-Host ''
    } catch {
        Write-Host $output
    }
    exit 0
}

Write-Host ''
Write-Host '保存命令执行失败。' -ForegroundColor Red
Write-Host '请先运行 3-测试连接.bat，确认连接正常。'
Write-Host ''
Write-Host $output
exit $exitCode
