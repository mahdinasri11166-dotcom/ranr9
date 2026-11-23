@echo off
REM Primary GUI launcher — always leaves a readable log; pauses on error
setlocal EnableExtensions EnableDelayedExpansion
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1
cd /d "%~dp0"
title GGUF Runner
set "GGUF_ROOT=%~dp0"
if "%GGUF_ROOT:~-1%"=="\" set "GGUF_ROOT=%GGUF_ROOT:~0,-1%"

if not exist "%~dp0logs" mkdir "%~dp0logs" 2>nul
set "LOG=%~dp0logs\launch.log"
echo ===== %DATE% %TIME% =====> "%LOG%"
echo ROOT=%GGUF_ROOT%>> "%LOG%"

call "%~dp0scripts\detect_windows.bat" 2>nul
if defined GGUF_OS_CLASS set "GGUF_OS_CLASS=%GGUF_OS_CLASS%"
echo OS_CLASS=%GGUF_OS_CLASS%>> "%LOG%"

set "PY="
if /I "%GGUF_OS_CLASS%"=="legacy" (
  if exist "%~dp0python38\python.exe" set "PY=%~dp0python38\python.exe"
) else (
  if exist "%~dp0python\python.exe" set "PY=%~dp0python\python.exe"
  if not defined PY if exist "%~dp0python38\python.exe" set "PY=%~dp0python38\python.exe"
)
if not defined PY if exist "%~dp0python38\python.exe" set "PY=%~dp0python38\python.exe"
if not defined PY if exist "%~dp0python\python.exe" set "PY=%~dp0python\python.exe"

if not defined PY (
  echo [ERROR] python.exe not found in python\ or python38\
  echo [ERROR] python.exe not found>> "%LOG%"
  echo Install path: %~dp0
  echo See logs\launch.log
  pause
  exit /b 1
)

echo Using: %PY%
echo Using: %PY%>> "%LOG%"

REM Tcl/Tk paths for embedded Python
for %%D in ("%~dp0python" "%~dp0python38") do (
  if exist "%%~D\tcl\tcl8.6" set "TCL_LIBRARY=%%~D\tcl\tcl8.6"
  if exist "%%~D\tcl\tk8.6" set "TK_LIBRARY=%%~D\tcl\tk8.6"
  if exist "%%~D\DLLs" set "PATH=%%~D;%%~D\DLLs;%%~D\Scripts;%PATH%"
)
REM Prefer the chosen PY home on PATH
for %%I in ("%PY%") do set "PYHOME=%%~dpI"
set "PATH=%PYHOME%;%PYHOME%DLLs;%PYHOME%Scripts;%PATH%"
if exist "%PYHOME%tcl\tcl8.6" set "TCL_LIBRARY=%PYHOME%tcl\tcl8.6"
if exist "%PYHOME%tcl\tk8.6" set "TK_LIBRARY=%PYHOME%tcl\tk8.6"
echo TCL_LIBRARY=%TCL_LIBRARY%>> "%LOG%"
echo TK_LIBRARY=%TK_LIBRARY%>> "%LOG%"

"%PY%" -c "import sys; print(sys.version)" >> "%LOG%" 2>&1
if errorlevel 1 (
  echo [ERROR] Python failed to start. See logs\launch.log
  type "%LOG%"
  pause
  exit /b 1
)

echo Checking tkinter... >> "%LOG%"
"%PY%" -c "import tkinter; print('tkinter OK')" >> "%LOG%" 2>&1
if errorlevel 1 (
  echo [ERROR] tkinter missing — GUI cannot start.
  echo [ERROR] tkinter missing>> "%LOG%"
  echo.
  echo Fix: reinstall full Setup from GitHub Actions ^(with tkinter injection^).
  echo Log: %LOG%
  echo.
  type "%LOG%"
  pause
  exit /b 1
)

echo Checking customtkinter... >> "%LOG%"
"%PY%" -c "import customtkinter; print('ctk OK', customtkinter.__version__)" >> "%LOG%" 2>&1
if errorlevel 1 (
  echo [WARN] customtkinter missing — trying pip install...
  "%PY%" -m pip install --disable-pip-version-check customtkinter >> "%LOG%" 2>&1
  "%PY%" -c "import customtkinter" >> "%LOG%" 2>&1
  if errorlevel 1 (
    echo [ERROR] customtkinter still missing. See logs\launch.log
    type "%LOG%"
    pause
    exit /b 1
  )
)

if not exist "%~dp0scripts\python\app_hub.py" (
  echo [ERROR] scripts\python\app_hub.py not found
  pause
  exit /b 1
)

echo Starting UI... >> "%LOG%"
echo Starting GGUF Runner UI...
"%PY%" "%~dp0scripts\python\app_hub.py" >> "%LOG%" 2>&1
set ERR=!ERRORLEVEL!
echo Exit code !ERR! >> "%LOG%"
if not "!ERR!"=="0" (
  echo.
  echo [ERROR] UI exited with code !ERR!
  echo Full log:
  echo ----------------------------------------
  type "%LOG%"
  echo ----------------------------------------
  echo Log file: %LOG%
  pause
  exit /b !ERR!
)
exit /b 0
