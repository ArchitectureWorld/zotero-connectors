@echo off
chcp 65001 >nul
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0安装工具\open-extension-page.ps1"
echo.
echo 完成后，再双击 3-测试连接.bat
echo.
pause
