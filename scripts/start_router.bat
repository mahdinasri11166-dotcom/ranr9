@echo off
chcp 65001 >nul
cd /d "%~dp0python"
echo Router http://127.0.0.1:8770
call "%~dp0run_py.bat" "%~dp0python\model_router.py"
if errorlevel 1 pause
pause
