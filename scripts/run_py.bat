@echo off
setlocal
set "SCRIPT_DIR=%~dp0"
for %%I in ("%SCRIPT_DIR%..") do set "ROOT=%%~fI"
set "GGUF_ROOT=%ROOT%"
call "%SCRIPT_DIR%env_python.bat"

if exist "%ROOT%\python\python.exe" (
  "%ROOT%\python\python.exe" %*
  exit /b %ERRORLEVEL%
)
where python >nul 2>&1
if %ERRORLEVEL%==0 (
  python %*
  exit /b %ERRORLEVEL%
)
echo [ERROR] No python found. Run SETUP.bat first.
exit /b 1
