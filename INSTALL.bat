@echo off
chcp 65001 >nul 2>&1
title GGUF Runner - Installer
setlocal EnableDelayedExpansion

echo.
echo  ========================================================
echo    GGUF Runner v0.4 - نصب‌کننده
echo    Windows 7 / 10 / 11
echo  ========================================================
echo.

set "SOURCE=%~dp0"
if "%SOURCE:~-1%"=="\" set "SOURCE=%SOURCE:~0,-1%"

set "DEFAULT_DIR=%USERPROFILE%\GGUF-Runner"
echo  مسیر پیش‌فرض: %DEFAULT_DIR%
set /p "INSTALL_DIR=  مسیر نصب (Enter=پیش‌فرض): "
if "!INSTALL_DIR!"=="" set "INSTALL_DIR=%DEFAULT_DIR%"
if "!INSTALL_DIR:~-1!"=="\" set "INSTALL_DIR=!INSTALL_DIR:~0,-1!"

echo.
echo  نصب در: !INSTALL_DIR!
if not exist "!INSTALL_DIR!" mkdir "!INSTALL_DIR!" 2>nul
if errorlevel 1 (
  echo  [خطا] ساخت پوشه ناموفق
  pause
  exit /b 1
)

echo  کپی فایل‌ها...
xcopy "%SOURCE%\*" "!INSTALL_DIR%\" /E /I /Y /Q >nul 2>&1
if not exist "!INSTALL_DIR!\bin" mkdir "!INSTALL_DIR!\bin"
if not exist "!INSTALL_DIR!\models" mkdir "!INSTALL_DIR!\models"

echo  ساخت میانبر دسکتاپ...
set "VBS=%TEMP%\gguf_sc.vbs"
(
  echo Set oWS = WScript.CreateObject^("WScript.Shell"^)
  echo sLinkFile = oWS.SpecialFolders^("Desktop"^) ^& "\GGUF Runner.lnk"
  echo Set oLink = oWS.CreateShortcut^(sLinkFile^)
  echo oLink.TargetPath = "!INSTALL_DIR!\GGUF-Runner.bat"
  echo oLink.WorkingDirectory = "!INSTALL_DIR!"
  echo oLink.Description = "GGUF Runner - Local AI"
  echo oLink.Save
) > "%VBS%"
cscript //nologo "%VBS%" >nul 2>&1
del "%VBS%" >nul 2>&1

set "STARTMENU=%APPDATA%\Microsoft\Windows\Start Menu\Programs"
if exist "%STARTMENU%" (
  set "VBS2=%TEMP%\gguf_sm.vbs"
  (
    echo Set oWS = WScript.CreateObject^("WScript.Shell"^)
    echo sLinkFile = "%STARTMENU%\GGUF Runner.lnk"
    echo Set oLink = oWS.CreateShortcut^(sLinkFile^)
    echo oLink.TargetPath = "!INSTALL_DIR!\GGUF-Runner.bat"
    echo oLink.WorkingDirectory = "!INSTALL_DIR!"
    echo oLink.Save
  ) > "%VBS2%"
  cscript //nologo "%VBS2%" >nul 2>&1
  del "%VBS2%" >nul 2>&1
)

echo !INSTALL_DIR!> "%USERPROFILE%\.gguf_runner_path.txt"

echo.
echo  ========================================================
echo    نصب انجام شد.
echo    مسیر: !INSTALL_DIR!
echo    میانبر: GGUF Runner (دسکتاپ)
echo.
echo    بعد از نصب:
echo    1. llama-server.exe → پوشه bin
echo    2. فایل‌های .gguf → پوشه models
echo    3. اجرای میانبر
echo  ========================================================
echo.
pause
