@echo off
chcp 65001 >nul
title Install psutil
cd /d "%~dp0.."

call "%~dp0detect_windows.bat" 2>nul
call "%~dp0env_python.bat" 2>nul

set "PY="
if /I "%GGUF_OS_CLASS%"=="legacy" (
  if exist "%~dp0..\python38\python.exe" set "PY=%~dp0..\python38\python.exe"
) else (
  if exist "%~dp0..\python\python.exe" set "PY=%~dp0..\python\python.exe"
  if not defined PY if exist "%~dp0..\python38\python.exe" set "PY=%~dp0..\python38\python.exe"
)
if not defined PY if exist "%~dp0..\python38\python.exe" set "PY=%~dp0..\python38\python.exe"
if not defined PY if exist "%~dp0..\python\python.exe" set "PY=%~dp0..\python\python.exe"

if not defined PY (
  echo [ERROR] Python not found. Install the app first.
  pause
  exit /b 1
)

echo Using: %PY%
"%PY%" -m pip install --upgrade pip
"%PY%" -m pip install "psutil>=5.9.0"
echo.
"%PY%" -c "import psutil; print('OK psutil', psutil.__version__); print('CPU%%', psutil.cpu_percent(0.2)); print('RAM%%', psutil.virtual_memory().percent)"
echo.
echo Done. Restart CHAT.bat then try: /monitor
pause
