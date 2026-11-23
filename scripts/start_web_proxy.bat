@echo off
chcp 65001 >nul
cd /d "%~dp0python"
echo Web proxy http://127.0.0.1:8766
call "%~dp0run_py.bat" "%~dp0python\web_proxy.py"
if errorlevel 1 pause
pause
