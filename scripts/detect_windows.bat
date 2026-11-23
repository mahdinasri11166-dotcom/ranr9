@echo off
REM Sets GGUF_OS_CLASS=legacy|modern
REM legacy = Windows 7 (6.1) and Windows 8.0 (6.2)  → Python 3.8
REM modern = Windows 8.1+ / 10 / 11                 → Python 3.11
set "GGUF_OS_CLASS=modern"
set "GGUF_OS_VER="

REM Method 1: ver
for /f "tokens=*" %%A in ('ver 2^>nul') do set "GGUF_OS_VER=%%A"
echo %GGUF_OS_VER% | findstr /I "6.1." >nul && set "GGUF_OS_CLASS=legacy"
echo %GGUF_OS_VER% | findstr /I "6.2." >nul && set "GGUF_OS_CLASS=legacy"
echo %GGUF_OS_VER% | findstr /I "Version 6.1" >nul && set "GGUF_OS_CLASS=legacy"
echo %GGUF_OS_VER% | findstr /I "Version 6.2" >nul && set "GGUF_OS_CLASS=legacy"

REM Method 2: WMIC (more reliable on Win7)
for /f "tokens=2 delims==" %%V in ('wmic os get Version /value 2^>nul ^| findstr /I "Version="') do (
  set "GGUF_WMIC_VER=%%V"
)
if defined GGUF_WMIC_VER (
  echo %GGUF_WMIC_VER% | findstr /B "6.1." >nul && set "GGUF_OS_CLASS=legacy"
  echo %GGUF_WMIC_VER% | findstr /B "6.2." >nul && set "GGUF_OS_CLASS=legacy"
)

REM Method 3: registry CurrentVersion (5.1=XP, 6.1=7, 6.2=8, 6.3=8.1, 10.0=10/11)
for /f "tokens=3" %%R in ('reg query "HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion" /v CurrentVersion 2^>nul ^| findstr /I "CurrentVersion"') do (
  set "GGUF_REG_VER=%%R"
)
if "%GGUF_REG_VER%"=="6.1" set "GGUF_OS_CLASS=legacy"
if "%GGUF_REG_VER%"=="6.2" set "GGUF_OS_CLASS=legacy"

exit /b 0
