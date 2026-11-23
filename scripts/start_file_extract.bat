@echo off
chcp 65001 >nul
cd /d "%~dp0python"
echo PDF/Image extract http://127.0.0.1:8767
call "%~dp0run_py.bat" "%~dp0python\file_extract.py"
if errorlevel 1 pause
pause
