@echo off
chcp 65001 >nul 2>&1
title GGUF Runner - Select Model
setlocal EnableDelayedExpansion

set "APP_DIR=%~dp0"
if "%APP_DIR:~-1%"=="\" set "APP_DIR=%APP_DIR:~0,-1%"
cd /d "%APP_DIR%"

:: defaults
set "HOST=127.0.0.1"
set "PORT=8080"
set "MODEL="
set "NGL=0"
set "CTX=4096"
set "THREADS=4"
set "BIN_DIR=bin"
set "WEB_DIR=web"
set "MODELS_DIR=models"
set "TEMP=0.7"
set "MAX_TOKENS=2048"
set "TOP_P=0.9"
set "REPEAT_PENALTY=1.1"
set "SYSTEM_PROMPT="

if exist "%APP_DIR%\config.ini" (
    for /f "usebackq tokens=1,* delims==" %%a in ("%APP_DIR%\config.ini") do (
        set "key=%%a"
        set "val=%%b"
        if /i "!key!"=="host" set "HOST=!val!"
        if /i "!key!"=="port" set "PORT=!val!"
        if /i "!key!"=="model" set "MODEL=!val!"
        if /i "!key!"=="n_gpu_layers" set "NGL=!val!"
        if /i "!key!"=="ctx_size" set "CTX=!val!"
        if /i "!key!"=="threads" set "THREADS=!val!"
        if /i "!key!"=="bin_dir" set "BIN_DIR=!val!"
        if /i "!key!"=="web_dir" set "WEB_DIR=!val!"
        if /i "!key!"=="models_dir" set "MODELS_DIR=!val!"
        if /i "!key!"=="temperature" set "TEMP=!val!"
        if /i "!key!"=="max_tokens" set "MAX_TOKENS=!val!"
        if /i "!key!"=="top_p" set "TOP_P=!val!"
        if /i "!key!"=="repeat_penalty" set "REPEAT_PENALTY=!val!"
        if /i "!key!"=="system_prompt" set "SYSTEM_PROMPT=!val!"
    )
)

set "BIN_PATH=%APP_DIR%\%BIN_DIR%"
set "MODELS_PATH=%APP_DIR%\%MODELS_DIR%"
set "WEB_PATH=%APP_DIR%\%WEB_DIR%"

cls
echo.
echo  ========================================================
echo    انتخاب مدل GGUF
echo  ========================================================
echo.

if not exist "%BIN_PATH%\llama-server.exe" (
    echo  [خطا] llama-server.exe پیدا نشد.
    echo  مسیر: %BIN_PATH%\llama-server.exe
    echo.
    echo  راهنما: docs\HOW_TO_GET_BINARIES.md
    echo.
    pause
    exit /b 1
)

if not exist "%MODELS_PATH%" mkdir "%MODELS_PATH%" 2>nul

echo  مدل‌های موجود:
echo  --------------------------------------------------------
set "count=0"
set "found=0"

for %%f in ("%MODELS_PATH%\*.gguf") do (
    set /a count+=1
    set "model_!count!=%%~ff"
    set "name_!count!=%%~nxf"
    set /a size_mb=%%~zf/1048576 2>nul
    if !size_mb! lss 1 set "size_mb=^<1"
    echo   !count!. %%~nxf
    echo      حجم: !size_mb! MB
    echo.
    set "found=1"
)

if "!found!"=="0" (
    echo.
    echo  هیچ فایل .gguf پیدا نشد.
    echo.
    echo  مدل‌های GGUF را داخل این پوشه کپی کنید:
    echo  %MODELS_PATH%
    echo.
    pause
    exit /b 1
)

echo  --------------------------------------------------------
echo  تعداد: !count! مدل
echo.

if !count! equ 1 (
    set "MODEL=!model_1!"
    set "SELECTED_NAME=!name_1!"
    echo  فقط یک مدل وجود دارد ← خودکار انتخاب شد
    echo  !SELECTED_NAME!
    echo.
    goto :ready
)

if defined MODEL (
    if exist "!MODEL!" (
        for %%x in ("!MODEL!") do set "PREV_NAME=%%~nxx"
        echo  آخرین مدل: !PREV_NAME!
        set /p "confirm=  دوباره همین مدل؟ [Y/n]: "
        if /i "!confirm!"=="n" goto :choose
        if /i "!confirm!"=="N" goto :choose
        set "SELECTED_NAME=!PREV_NAME!"
        goto :ready
    )
)

:choose
echo  شماره مدل (1-!count!):
set /p "choice=  > "
if "!choice!"=="" set "choice=1"
set "valid=0"
for /l %%i in (1,1,!count!) do if "!choice!"=="%%i" set "valid=1"
if "!valid!"=="0" (
    echo  نامعتبر ← مدل 1 انتخاب شد
    set "choice=1"
)
set "MODEL=!model_%choice%!"
set "SELECTED_NAME=!name_%choice%!"

:ready
echo.
echo  --------------------------------------------------------
echo  مدل     : !SELECTED_NAME!
echo  Host    : %HOST%:%PORT%
echo  Context : %CTX%   Threads: %THREADS%   GPU layers: %NGL%
echo  Temp    : %TEMP%  Max tokens: %MAX_TOKENS%
echo  --------------------------------------------------------
echo.

:: save config
(
    echo [server]
    echo host=%HOST%
    echo port=%PORT%
    echo model=%MODEL%
    echo n_gpu_layers=%NGL%
    echo ctx_size=%CTX%
    echo threads=%THREADS%
    echo.
    echo [ui]
    echo temperature=%TEMP%
    echo max_tokens=%MAX_TOKENS%
    echo top_p=%TOP_P%
    echo repeat_penalty=%REPEAT_PENALTY%
    echo system_prompt=%SYSTEM_PROMPT%
    echo.
    echo [paths]
    echo bin_dir=%BIN_DIR%
    echo models_dir=%MODELS_DIR%
    echo web_dir=%WEB_DIR%
) > "%APP_DIR%\config.ini"

:: stop previous
taskkill /F /IM llama-server.exe >nul 2>&1
timeout /t 1 /nobreak >nul

echo  در حال راه‌اندازی سرور...
start "llama-server" /min "%BIN_PATH%\llama-server.exe" ^
    -m "%MODEL%" ^
    --host %HOST% ^
    --port %PORT% ^
    -c %CTX% ^
    -t %THREADS% ^
    -ngl %NGL% ^
    --path "%WEB_PATH%"

echo  منتظر بالا آمدن سرور...
timeout /t 4 /nobreak >nul

start "" "http://%HOST%:%PORT%"

echo.
echo  سرور روشن شد. صفحه چت باز شد.
echo  برای توقف از منوی اصلی گزینه 2 را بزنید.
echo.
pause
