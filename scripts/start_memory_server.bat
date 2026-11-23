@echo off
chcp 65001 >nul
cd /d "%~dp0python"
echo RAG server http://127.0.0.1:8765
call "%~dp0run_py.bat" "%~dp0python\memory_server.py"
if errorlevel 1 pause
pause
