@echo off
chcp 65001 >nul
set "D=%~dp0"
start "vector-rag" cmd /k "%D%start_memory_server.bat"
start "web-proxy" cmd /k "%D%start_web_proxy.bat"
start "model-router" cmd /k "%D%start_router.bat"
start "file-extract" cmd /k "%D%start_file_extract.bat"
echo Started: RAG :8765 | Proxy :8766 | Router :8770 | PDF/Image :8767
start "openai-api" cmd /k "%~dp0start_openai_api.bat"
echo Also: OpenAI API :8787
