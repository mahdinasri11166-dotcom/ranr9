@echo off
chcp 65001 >nul 2>&1
setlocal EnableDelayedExpansion

set "APP_DIR=%~dp0.."
if "%APP_DIR:~-1%"=="\" set "APP_DIR=%APP_DIR:~0,-1%"
cd /d "%APP_DIR%"

if not exist "%APP_DIR%\memory" mkdir "%APP_DIR%\memory"
if not exist "%APP_DIR%\books" mkdir "%APP_DIR%\books"
if not exist "%APP_DIR%\web" mkdir "%APP_DIR%\web"
if not exist "%APP_DIR%\dataset" mkdir "%APP_DIR%\dataset"

set "OUT=%APP_DIR%\web\memory_context.txt"
echo. > "%OUT%"
echo ===== MEMORY CONTEXT (auto-generated) =====>> "%OUT%"
echo Generated: %DATE% %TIME%>> "%OUT%"
echo.>> "%OUT%"

:: جمع‌آوری حافظه‌های متنی
echo --- Chat memories --->> "%OUT%"
set "mc=0"
for %%f in ("%APP_DIR%\memory\*.txt") do (
  set /a mc+=1
  echo [memory: %%~nxf]>> "%OUT%"
  type "%%f" >> "%OUT%" 2>nul
  echo.>> "%OUT%"
  echo.>> "%OUT%"
)

echo --- Books --->> "%OUT%"
set "bc=0"
for %%f in ("%APP_DIR%\books\*.txt") do (
  set /a bc+=1
  echo [book: %%~nxf]>> "%OUT%"
  :: فقط اول ۵۰ کیلوبایت تقریبی برای جلوگیری از فایل خیلی بزرگ
  powershell -Command "Get-Content -Path '%%f' -TotalCount 800 -ErrorAction SilentlyContinue" >> "%OUT%" 2>nul
  if errorlevel 1 (
    :: fallback بدون powershell (Win7 قدیمی)
    more +0 "%%f" >> "%OUT%" 2>nul
  )
  echo.>> "%OUT%"
  echo.>> "%OUT%"
)

echo.
echo حافظه ساخته شد: web\memory_context.txt
echo تعداد فایل حافظه: !mc!
echo تعداد کتاب: !bc!
