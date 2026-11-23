@echo off
REM Called by NSIS after files are copied. Detects Windows and records preferred Python.
setlocal EnableExtensions
cd /d "%~dp0.."
set "INSTROOT=%cd%"

call "%~dp0detect_windows.bat" 2>nul

if not exist "%INSTROOT%\profiles" mkdir "%INSTROOT%\profiles" 2>nul
if not exist "%INSTROOT%\installer" mkdir "%INSTROOT%\installer" 2>nul

(
  echo GGUF_OS_CLASS=%GGUF_OS_CLASS%
  echo GGUF_WMIC_VER=%GGUF_WMIC_VER%
  echo GGUF_REG_VER=%GGUF_REG_VER%
  echo GGUF_OS_VER=%GGUF_OS_VER%
  echo DETECTED_AT=%DATE% %TIME%
) > "%INSTROOT%\profiles\os_class.txt"

(
  echo GGUF Windows detect log
  echo INSTROOT=%INSTROOT%
  echo GGUF_OS_CLASS=%GGUF_OS_CLASS%
  echo GGUF_WMIC_VER=%GGUF_WMIC_VER%
  echo GGUF_REG_VER=%GGUF_REG_VER%
  echo GGUF_OS_VER=%GGUF_OS_VER%
  if exist "%INSTROOT%\python38\python.exe" (echo python38=YES) else (echo python38=NO)
  if exist "%INSTROOT%\python\python.exe" (echo python311=YES) else (echo python311=NO)
) > "%INSTROOT%\installer\detect_log.txt"

REM Preferred python marker for launchers
if /I "%GGUF_OS_CLASS%"=="legacy" (
  if exist "%INSTROOT%\python38\python.exe" (
    echo python38>"%INSTROOT%\profiles\preferred_python.txt"
    echo LEGACY: preferred python38
  ) else (
    echo MISSING>"%INSTROOT%\profiles\preferred_python.txt"
    echo LEGACY: python38 MISSING
  )
) else (
  if exist "%INSTROOT%\python\python.exe" (
    echo python>"%INSTROOT%\profiles\preferred_python.txt"
    echo MODERN: preferred python
  ) else if exist "%INSTROOT%\python38\python.exe" (
    echo python38>"%INSTROOT%\profiles\preferred_python.txt"
    echo MODERN: fallback python38
  ) else (
    echo MISSING>"%INSTROOT%\profiles\preferred_python.txt"
  )
)

exit /b 0
