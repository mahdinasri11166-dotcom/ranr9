@echo off
chcp 65001 >nul
cd /d "%~dp0python"
echo OpenAI-compatible API on http://127.0.0.1:8787
echo Use from other apps as base_url=http://127.0.0.1:8787/v1
call "%~dp0run_py.bat" "%~dp0python\openai_api_server.py"
if errorlevel 1 pause
pause
