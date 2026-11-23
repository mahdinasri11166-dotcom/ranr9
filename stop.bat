@echo off
taskkill /f /im llama-server.exe >nul 2>&1
echo llama-server stopped (if it was running)
