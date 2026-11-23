@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo Model parameters are in the RIGHT panel of Desktop Chat.
echo Config file: desktop_chat_config.json
echo.
if exist "desktop_chat_config.json" (
  echo Opening config...
  notepad "desktop_chat_config.json"
)
echo Launching chat...
call "%~dp0CHAT.bat"
