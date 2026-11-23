@echo off
chcp 65001 >nul
setlocal EnableDelayedExpansion
set "APP_DIR=%~dp0"
if "%APP_DIR:~-1%"=="\" set "APP_DIR=%APP_DIR:~0,-1%"
cd /d "%APP_DIR%"

if not exist "%APP_DIR%\bin\llama-server.exe" (
  echo Missing bin\llama-server.exe
  pause & exit /b 1
)

echo ========================================================
echo  Multi-model launcher  - Mehdi Tariri
echo  Starts up to 2 GGUF models on ports 8080 and 8081
echo ========================================================
echo.

set /a n=0
for %%f in ("%APP_DIR%\models\*.gguf") do (
  set /a n+=1
  echo  !n!. %%~nxf
  set "m!n!=%%f"
)
if %n%==0 ( echo No GGUF in models\ & pause & exit /b 1 )

set /p a= Model index for port 8080: 
set /p b= Model index for port 8081 (empty=skip): 

set "exe=%APP_DIR%\bin\llama-server.exe"
set "CTX=4096"
if exist "%APP_DIR%\config.ini" for /f "usebackq tokens=1,* delims==" %%x in ("%APP_DIR%\config.ini") do if /i "%%x"=="ctx_size" set "CTX=%%y"

if defined m%a% (
  for %%P in (!m%a%!) do (
    echo Starting 8080: %%~nxP
    start "llama-8080" "%exe%" -m "%%~P" --port 8080 --host 127.0.0.1 -c %CTX% --path "%APP_DIR%\web"
  )
)
if not "%b%"=="" if defined m%b% (
  for %%P in (!m%b%!) do (
    echo Starting 8081: %%~nxP
    start "llama-8081" "%exe%" -m "%%~P" --port 8081 --host 127.0.0.1 -c %CTX%
  )
)

echo.
echo Chat UI: http://127.0.0.1:8080
echo Second API: http://127.0.0.1:8081/v1/chat/completions
timeout /t 3 >nul
start "" "http://127.0.0.1:8080"
pause
