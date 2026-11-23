@echo off
chcp 65001 >nul
title GGUF Doctor
cd /d "%~dp0.."
echo.
call "%~dp0run_py.bat" "%~dp0python\doctor.py"
echo.
pause
