@echo off
REM Resolve offline Python home for current Windows
set "GGUF_ROOT=%~dp0.."
if exist "%~dp0..\CHAT.bat" set "GGUF_ROOT=%~dp0.."
if exist "%cd%\CHAT.bat" set "GGUF_ROOT=%cd%"

call "%~dp0detect_windows.bat" 2>nul

set "GGUF_PY_HOME="
if /I "%GGUF_OS_CLASS%"=="legacy" (
  if exist "%GGUF_ROOT%\python38\python.exe" set "GGUF_PY_HOME=%GGUF_ROOT%\python38"
  if not defined GGUF_PY_HOME if exist "%GGUF_ROOT%\python\python.exe" (
    REM Do NOT use 3.11 on Win7 — leave empty so caller errors clearly
    set "GGUF_PY_HOME="
  )
) else (
  if exist "%GGUF_ROOT%\python\python.exe" set "GGUF_PY_HOME=%GGUF_ROOT%\python"
  if not defined GGUF_PY_HOME if exist "%GGUF_ROOT%\python38\python.exe" set "GGUF_PY_HOME=%GGUF_ROOT%\python38"
)

if not defined GGUF_PY_HOME exit /b 1

set "PATH=%GGUF_PY_HOME%;%GGUF_PY_HOME%\Scripts;%GGUF_PY_HOME%\DLLs;%PATH%"
if exist "%GGUF_PY_HOME%\tcl\tcl8.6" set "TCL_LIBRARY=%GGUF_PY_HOME%\tcl\tcl8.6"
if exist "%GGUF_PY_HOME%\tcl\tk8.6" set "TK_LIBRARY=%GGUF_PY_HOME%\tcl\tk8.6"
exit /b 0
