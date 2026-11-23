@echo off
chcp 65001 >nul
cd /d "%~dp0"
call bootstrap.bat
echo.
echo Opening docs folder...
if exist docs explorer docs
echo.
echo Starting main menu...
call GGUF-Runner.bat
