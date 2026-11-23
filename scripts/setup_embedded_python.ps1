# Install embeddable Python into app\python\ based on Windows version
# Mehdi Tariri <mahditariri@gmail.com>
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
if (-not (Test-Path (Join-Path $Root "GGUF-Runner.bat"))) { $Root = Get-Location }
Set-Location $Root

$PyDir = Join-Path $Root "python"
$Payload = Join-Path $Root "installer\payload"

# Detect OS build
$build = 0
try { $build = [int](Get-CimInstance Win32_OperatingSystem).BuildNumber } catch {}
$is64 = [Environment]::Is64BitOperatingSystem

Write-Host "=== Embedded Python setup ==="
Write-Host "Build=$build  64bit=$is64  Root=$Root"

# Choose version: Win7 (build<=7601-ish, <9200 for win8) use 3.8; else 3.11
# Win7 build 7600/7601; Win8 9200; Win8.1 9600; Win10 10240+
if ($build -gt 0 -and $build -lt 9200) {
  $ver = "3.8.10"
  $tag = "win7"
} else {
  $ver = "3.11.9"
  $tag = "win10plus"
}

$arch = if ($is64) { "amd64" } else { "win32" }
$zipName = "python-$ver-embed-$arch.zip"
$prebaked = Join-Path $Payload $zipName
$prebakedDir = Join-Path $Payload "python-$ver-$arch"

function Enable-Pth($dir) {
  $pth = Get-ChildItem -Path $dir -Filter "python*._pth" | Select-Object -First 1
  if ($pth) {
    $c = Get-Content $pth.FullName -Raw
    if ($c -notmatch "(?m)^import site") {
      $c = $c -replace "(?m)^#import site","import site"
      if ($c -notmatch "(?m)^import site") { $c = $c.TrimEnd() + "`r`nimport site`r`n" }
      Set-Content -Path $pth.FullName -Value $c -NoNewline
    }
  }
}

function Install-Pip($pyExe) {
  $getpip = Join-Path $PyDir "get-pip.py"
  if (-not (Test-Path $getpip)) {
    $localGet = Join-Path $Payload "get-pip.py"
    if (Test-Path $localGet) { Copy-Item $localGet $getpip }
    else {
      Invoke-WebRequest -Uri "https://bootstrap.pypa.io/get-pip.py" -OutFile $getpip -UseBasicParsing
    }
  }
  & $pyExe $getpip --no-warn-script-location
}

# Already installed?
$pyExe = Join-Path $PyDir "python.exe"
if ((Test-Path $pyExe) -and $env:GGUF_FORCE_PYTHON -ne "1") {
  Write-Host "[OK] Embedded python already at $pyExe"
  & $pyExe --version
} else {
  New-Item -ItemType Directory -Force -Path $PyDir | Out-Null
  $tmp = Join-Path $Root "bin\_py_tmp"
  New-Item -ItemType Directory -Force -Path $tmp | Out-Null

  if (Test-Path $prebakedDir) {
    Write-Host "[..] Using prebaked payload $prebakedDir"
    Copy-Item -Recurse -Force "$prebakedDir\*" $PyDir
  } elseif (Test-Path $prebaked) {
    Write-Host "[..] Extracting payload $zipName"
    Expand-Archive -Path $prebaked -DestinationPath $PyDir -Force
  } else {
    $url = "https://www.python.org/ftp/python/$ver/$zipName"
    Write-Host "[..] Downloading $url"
    $zipPath = Join-Path $tmp $zipName
    Invoke-WebRequest -Uri $url -OutFile $zipPath -UseBasicParsing
    Expand-Archive -Path $zipPath -DestinationPath $PyDir -Force
  }

  Enable-Pth $PyDir
  $pyExe = Join-Path $PyDir "python.exe"
  if (-not (Test-Path $pyExe)) { throw "python.exe missing after extract" }
  Write-Host "[OK] $($pyExe) version:"
  & $pyExe --version
  Write-Host "[..] Installing pip..."
  Install-Pip $pyExe
  Remove-Item -Recurse -Force $tmp -EA SilentlyContinue
}

# pip install requirements
$req = Join-Path $Root "scripts\python\requirements.txt"
if (Test-Path $req) {
  Write-Host "[..] pip install -r requirements.txt"
  try {
    & $pyExe -m pip install --upgrade pip
    & $pyExe -m pip install -r $req
    Write-Host "[OK] Python libraries installed"
    Write-Host "[..] llama-cpp-python + customtkinter for desktop chat..."
    try { & $pyExe -m pip install llama-cpp-python customtkinter psutil } catch { Write-Host "[WARN] desktop deps: $($_.Exception.Message)" }
  } catch {
    Write-Host "[WARN] pip packages: $($_.Exception.Message)"
  }
}

# helper launcher
$launcher = Join-Path $Root "python_env.bat"
@"
@echo off
set "PATH=$PyDir;%PATH%"
set "PYTHONHOME=$PyDir"
"$PyDir\python.exe" %*
"@ | Set-Content -Path $launcher -Encoding ASCII

Write-Host "[OK] Embedded Python ready ($ver / $tag)"
Write-Host "     Use: python\python.exe  or  python_env.bat"
