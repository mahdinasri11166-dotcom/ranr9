@echo off
chcp 65001 >nul
cd /d "%~dp0"
if not exist Output mkdir Output
where makensis >nul 2>&1
if errorlevel 1 (
  echo Install NSIS from https://nsis.sourceforge.io/Download
  echo Or: choco install nsis
  pause
  exit /b 1
)
makensis /V2 GGUF-Runner.nsi
echo.
echo Output: installer\Output\
dir Output\*.exe
pause
