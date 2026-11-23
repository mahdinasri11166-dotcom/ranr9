$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root
function Ok($m){ Write-Host "[OK] $m" -ForegroundColor Green }
function Bad($m){ Write-Host "[!!] $m" -ForegroundColor Red }
function Info($m){ Write-Host "[..] $m" -ForegroundColor Yellow }
Write-Host "=== GGUF Runner Doctor ===" -ForegroundColor Cyan
Write-Host "Root: $Root"
if (Test-Path "bin\llama-server.exe") { Ok "llama-server.exe" } else { Bad "bin\llama-server.exe — run SETUP.bat" }
$mc = @(Get-ChildItem models\*.gguf -EA SilentlyContinue).Count
if ($mc -gt 0) { Ok "$mc GGUF model(s)" } else { Bad "no models in models\" }
if (Test-Path "python\python.exe") {
  Ok "embedded python\python.exe"
  try { & "python\python.exe" --version } catch {}
} else { Info "no embedded python — SETUP.bat installs it" }
$sys = Get-Command python -EA SilentlyContinue
if ($sys) { Ok "system python in PATH" }
if (Test-Path "web\index.html") { Ok "web\index.html" } else { Bad "web UI missing" }
if (Test-Path "scripts\python\file_extract.py") { Ok "file_extract.py" } else { Bad "file_extract missing" }
foreach ($u in @(
  @{n="LLM"; u="http://127.0.0.1:8080/health"},
  @{n="RAG"; u="http://127.0.0.1:8765/health"},
  @{n="Proxy"; u="http://127.0.0.1:8766/health"},
  @{n="Router"; u="http://127.0.0.1:8770/health"},
  @{n="PDF"; u="http://127.0.0.1:8767/health"}
)) {
  try {
    $r = Invoke-WebRequest -Uri $u.u -UseBasicParsing -TimeoutSec 2
    Ok "$($u.n) online"
  } catch { Info "$($u.n) offline" }
}
Write-Host "Run: scripts\python\selftest.py for module tests"
Write-Host "=== done ==="
