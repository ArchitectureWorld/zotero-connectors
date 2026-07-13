@echo off
chcp 65001 >nul
setlocal

echo ==============================================
echo Zotero Connector 自动化组件一键安装
echo ==============================================
echo.

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0安装工具\install-all.ps1"
set "EXIT_CODE=%ERRORLEVEL%"

echo.
if not "%EXIT_CODE%"=="0" (
    echo 安装未完成，请保留本窗口中的错误信息。
) else (
    echo 安装与自检已经完成，可以关闭此窗口。
)
echo.
pause
exit /b %EXIT_CODE%
