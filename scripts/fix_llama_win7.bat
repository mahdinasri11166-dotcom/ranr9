@echo off
REM Reinstall older llama-cpp-python for Windows 7 (fixes SetThreadInformation / KERNEL32)
setlocal
cd /d "%~dp0.."
set "PY="
if exist "%~dp0..\python38\python.exe" set "PY=%~dp0..\python38\python.exe"
if not defined PY if exist "%~dp0..\python\python.exe" set "PY=%~dp0..\python\python.exe"
if not defined PY (
  echo Python not found
  pause
  exit /b 1
)
echo Using %PY%
echo Uninstalling current llama-cpp-python...
"%PY%" -m pip uninstall -y llama-cpp-python
for %%V in (0.2.20 0.2.26 0.2.55 0.2.90) do (
  echo Trying llama-cpp-python==%%V ...
  "%PY%" -m pip install "llama-cpp-python==%%V" --prefer-binary
  "%PY%" -c "from llama_cpp import Llama; print('OK', '%%V')" && goto :ok
)
echo FAILED — try Windows 10/11 or build from source with older MSVC.
pause
exit /b 1
:ok
echo.
echo Success. Restart RUN_GUI.bat then load model with ctx=2048 ngl=0
pause
