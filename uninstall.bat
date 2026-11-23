@echo off
chcp 65001 >nul
title GGUF Runner Uninstall
cd /d "%~dp0"
echo This removes desktop shortcut and optional local data.
echo App folder must be deleted manually if installed via NSIS (use Uninstall from Start Menu).
echo.
set /p y=Remove desktop shortcut? [Y/N]: 
if /i "%y%"=="Y" (
  del "%USERPROFILE%\Desktop\GGUF Runner.lnk" 2>nul
  del "%USERPROFILE%\Desktop\GGUF Chat.lnk" 2>nul
  echo Shortcut removed.
)
echo Done.
pause
