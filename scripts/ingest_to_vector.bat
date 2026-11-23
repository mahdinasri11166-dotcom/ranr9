@echo off
chcp 65001 >nul
cd /d "%~dp0.."
echo Building local RAG index from books\ and memory\
call "%~dp0run_py.bat" "%~dp0python\ingest_books.py"
if errorlevel 1 pause
pause
