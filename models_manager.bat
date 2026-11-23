@echo off
chcp 65001 >nul
title Models Manager
cd /d "%~dp0"
if not exist models mkdir models
echo ========================================================
echo  Models folder: %CD%\models
echo  Mehdi Tariri
echo ========================================================
echo.
dir /b models\*.gguf 2>nul
if errorlevel 1 echo (no .gguf files yet)
echo.
echo 1 Open models folder
echo 2 Open Hugging Face GGUF search in browser
echo 0 Back
set /p c=Choice: 
if "%c%"=="1" explorer "%CD%\models"
if "%c%"=="2" start https://huggingface.co/models?search=GGUF
pause
