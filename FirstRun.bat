@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title GGUF Runner — First Run
if not exist "models" mkdir models 2>nul
if not exist "books" mkdir books 2>nul
if not exist "sessions" mkdir sessions 2>nul
if not exist "workspace" mkdir workspace 2>nul
if not exist "memory" mkdir memory 2>nul
if not exist "logs" mkdir logs 2>nul
call "%~dp0scripts\detect_windows.bat" 2>nul
echo OS class: %GGUF_OS_CLASS%
dir /b "models\*.gguf" >nul 2>&1
if errorlevel 1 (
  echo [INFO] No GGUF model yet — UI will still open.
)
echo Launching GUI...
call "%~dp0RUN_GUI.bat"
