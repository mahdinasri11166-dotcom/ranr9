@echo off
chcp 65001 >nul
setlocal
set "APP=%~dp0"
if "%APP:~-1%"=="\" set "APP=%APP:~0,-1%"
cd /d "%APP%"

echo ========================================================
echo  GGUF Runner bootstrap - Mehdi Tariri
echo ========================================================

for %%D in (bin models books memory memory\vectors dataset dataset\auto sessions workspace profiles) do (
  if not exist "%APP%\%%D" mkdir "%APP%\%%D"
)

echo.
echo [1/4] Checking llama-server.exe ...
if exist "%APP%\bin\llama-server.exe" (
  echo   OK: bin\llama-server.exe
) else (
  echo   MISSING: place llama-server.exe in bin\
  echo   See docs\HOW_TO_GET_BINARIES.md
)

echo.
echo [2/4] Checking models ...
set /a mc=0
for %%f in ("%APP%\models\*.gguf") do set /a mc+=1
if %mc%==0 (
  echo   No .gguf found in models\ - copy your models there
) else (
  echo   Found %mc% GGUF model(s)
)

echo.
echo [3/4] Checking Python ...
python --version >nul 2>&1
if errorlevel 1 (
  echo   Python not in PATH. Optional features need Python 3.10+
  echo   See docs\PYTHON_INSTALL.md
) else (
  python --version
  echo   To install optional deps:
  echo   cd scripts\python ^& pip install -r requirements.txt
)

echo.
echo [4/4] Shortcuts
echo   Main menu: GGUF-Runner.bat
echo.
pause
