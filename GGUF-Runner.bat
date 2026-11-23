@echo off
chcp 65001 >nul 2>&1
title GGUF Runner v2.4 - Mehdi Tariri / Mohsen Tarifii
setlocal EnableDelayedExpansion
set "APP_DIR=%~dp0"
if "%APP_DIR:~-1%"=="\" set "APP_DIR=%APP_DIR:~0,-1%"
cd /d "%APP_DIR%"

:menu
cls
echo.
echo  ========================================================
echo    GGUF Runner v2.4  (Desktop Chat)
echo    Mehdi Tariri / Mohsen Tarifii
echo  ========================================================
echo.
echo    1. Open App Hub UI  (recommended)
echo    A. Auto-setup (Python + llama-cpp-python + libs)
echo    W. First-run wizard (recommended for new install)
echo    D. Doctor
echo    T. Selftest
echo    4. Side services (RAG / Proxy / Router / PDF)
echo    5. One service
echo    6. Ingest books
echo    7. Build text memory
echo    8. LoRA pipeline
echo   10. Open models folder
echo    M. Models manager
echo   11. Other folders
echo   12. Docs
echo    0. Exit
echo.
set /p o=  Choice: 
if "%o%"=="1" (call "%APP_DIR%\CHAT.bat" & goto menu)
if /i "%o%"=="A" (call "%APP_DIR%\SETUP.bat" & goto menu)
if /i "%o%"=="W" (call "%APP_DIR%\FirstRun.bat" & goto menu)
if /i "%o%"=="D" (call "%APP_DIR%\scripts\doctor.bat" & goto menu)
if /i "%o%"=="T" (call "%APP_DIR%\scripts\run_py.bat" "%APP_DIR%\scripts\python\selftest.py" & pause & goto menu)
if "%o%"=="4" (call "%APP_DIR%\scripts\start_all_services.bat" & goto menu)
if "%o%"=="5" goto services
if "%o%"=="6" (call "%APP_DIR%\scripts\ingest_to_vector.bat" & goto menu)
if "%o%"=="7" (call "%APP_DIR%\scripts\build_memory.bat" & pause & goto menu)
if "%o%"=="8" (call "%APP_DIR%\scripts\run_py.bat" "%APP_DIR%\scripts\python\lora_pipeline.py" & pause & goto menu)
if "%o%"=="10" (explorer "%APP_DIR%\models" & goto menu)
if /i "%o%"=="M" (call "%APP_DIR%\models_manager.bat" & goto menu)
if "%o%"=="11" goto folders
if "%o%"=="12" (explorer "%APP_DIR%\docs" & goto menu)
if "%o%"=="0" exit /b 0
goto menu

:services
echo 1 RAG 8765  2 Proxy 8766  3 Router 8770  4 PDF 8767  5 OpenAI API 8787
set /p s=svc: 
if "%s%"=="1" start "rag" cmd /k "%APP_DIR%\scripts\start_memory_server.bat"
if "%s%"=="2" start "proxy" cmd /k "%APP_DIR%\scripts\start_web_proxy.bat"
if "%s%"=="3" start "router" cmd /k "%APP_DIR%\scripts\start_router.bat"
if "%s%"=="4" start "pdf" cmd /k "%APP_DIR%\scripts\start_file_extract.bat"
if "%s%"=="5" start "openai-api" cmd /k "%APP_DIR%\scripts\start_openai_api.bat"
goto menu

:folders
echo 1 models 2 memory 3 books 4 dataset 5 sessions 6 docs
set /p f=folder: 
if "%f%"=="1" explorer "%APP_DIR%\models"
if "%f%"=="2" explorer "%APP_DIR%\memory"
if "%f%"=="3" explorer "%APP_DIR%\books"
if "%f%"=="4" explorer "%APP_DIR%\dataset"
if "%f%"=="5" explorer "%APP_DIR%\sessions"
if "%f%"=="6" explorer "%APP_DIR%\docs"
goto menu
