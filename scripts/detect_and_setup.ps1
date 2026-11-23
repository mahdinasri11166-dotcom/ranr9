# Detect Windows + arch, install llama-server + embedded Python
# Mehdi Tariri <mahditariri@gmail.com>
$ErrorActionPreference = "Continue"
$Root = if ($PSScriptRoot) { Split-Path -Parent $PSScriptRoot } else { Get-Location }
if (-not (Test-Path (Join-Path $Root "GGUF-Runner.bat"))) {
  if (Test-Path (Join-Path $PSScriptRoot "..\GGUF-Runner.bat")) { $Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path }
  else { $Root = (Get-Location).Path }
}
Set-Location $Root

Write-Host "========================================================"
Write-Host " GGUF Runner — Full Setup"
Write-Host " Mehdi Tariri | mahditariri@gmail.com"
Write-Host "========================================================"

$os = $null
try { $os = Get-CimInstance Win32_OperatingSystem } catch {}
$caption = if ($os) { $os.Caption } else { "Windows" }
$build = if ($os) { [int]$os.BuildNumber } else { 0 }
$is64 = [Environment]::Is64BitOperatingSystem
$bits = if ($is64) { 64 } else { 32 }

$winLabel = "Windows"
if ($build -ge 22000) { $winLabel = "Windows 11" }
elseif ($build -ge 10240) { $winLabel = "Windows 10" }
elseif ($build -ge 9600) { $winLabel = "Windows 8.1" }
elseif ($build -ge 9200) { $winLabel = "Windows 8" }
elseif ($build -ge 7600) { $winLabel = "Windows 7" }

Write-Host "OS     : $caption"
Write-Host "Label  : $winLabel (build $build)"
Write-Host "Arch   : $bits-bit"
Write-Host "Root   : $Root"
Write-Host ""

if ($bits -eq 32) {
  Write-Host "[WARN] 32-bit: official llama.cpp is mainly 64-bit."
}
if ($winLabel -eq "Windows 7") {
  Write-Host "[INFO] Windows 7 → Python 3.8 embed + older-friendly server if needed"
}

foreach ($d in @("bin","models","books","memory","dataset","sessions","workspace","profiles","python")) {
  New-Item -ItemType Directory -Force -Path (Join-Path $Root $d) | Out-Null
}

# --- llama-server ---
$Bin = Join-Path $Root "bin"
$server = Join-Path $Bin "llama-server.exe"
$force = $env:GGUF_FORCE_DOWNLOAD -eq "1"
if ((Test-Path $server) -and -not $force) {
  Write-Host "[OK] llama-server.exe present"
} elseif ($bits -eq 32) {
  Write-Host "[SKIP] Auto llama-server is 64-bit only — place exe in bin\ manually"
} else {
  try {
    $headers = @{ "User-Agent" = "GGUF-Runner-Setup"; "Accept" = "application/vnd.github+json" }
    $releases = Invoke-RestMethod -Uri "https://api.github.com/repos/ggml-org/llama.cpp/releases?per_page=8" -Headers $headers
    $asset = $null
    foreach ($rel in $releases) {
      foreach ($a in $rel.assets) {
        $n = $a.name.ToLowerInvariant()
        if ($n -match "win" -and $n -match "x64" -and $n -match "cpu" -and $n -match "\.zip$" -and $n -notmatch "cuda") { $asset = $a; break }
      }
      if ($asset) { break }
    }
    if (-not $asset) {
      foreach ($rel in $releases) {
        foreach ($a in $rel.assets) {
          $n = $a.name.ToLowerInvariant()
          if ($n -match "win" -and $n -match "x64" -and $n -match "\.zip$" -and $n -notmatch "cuda") { $asset = $a; break }
        }
        if ($asset) { break }
      }
    }
    if (-not $asset) { throw "No Windows x64 zip on releases" }
    Write-Host "[..] Downloading $($asset.name)"
    $tmp = Join-Path $Bin "_tmp"
    New-Item -ItemType Directory -Force -Path $tmp | Out-Null
    $zip = Join-Path $tmp "llama.zip"
    Invoke-WebRequest -Uri $asset.browser_download_url -OutFile $zip -UseBasicParsing
    Expand-Archive -Path $zip -DestinationPath (Join-Path $tmp "out") -Force
    $exe = Get-ChildItem -Path (Join-Path $tmp "out") -Recurse -Filter "llama-server.exe" | Select-Object -First 1
    if (-not $exe) { $exe = Get-ChildItem -Path (Join-Path $tmp "out") -Recurse -Filter "server.exe" | Select-Object -First 1 }
    if (-not $exe) { throw "llama-server.exe not in archive" }
    Copy-Item -Force $exe.FullName $server
    Get-ChildItem -Path $exe.Directory.FullName -Filter "*.dll" -EA SilentlyContinue | Copy-Item -Force -Destination $Bin
    Remove-Item -Recurse -Force $tmp -EA SilentlyContinue
    Write-Host "[OK] llama-server installed"
  } catch {
    Write-Host "[FAIL] $($_.Exception.Message)"
  }
}

# --- Embedded Python ---
Write-Host ""
Write-Host "[..] Embedded Python (version matched to OS)..."
try {
  & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $Root "scripts\setup_embedded_python.ps1")
} catch {
  Write-Host "[WARN] Embedded Python: $($_.Exception.Message)"
  $sysPy = Get-Command python -EA SilentlyContinue
  if ($sysPy) {
    Write-Host "[..] Fallback system Python"
    try { & python -m pip install -r (Join-Path $Root "scripts\python\requirements.txt") } catch {}
  }
}

# --- Desktop shortcut ---
try {
  $Wsh = New-Object -ComObject WScript.Shell
  $desk = [Environment]::GetFolderPath("Desktop")
  $sc = $Wsh.CreateShortcut((Join-Path $desk "GGUF Runner.lnk"))
  $sc.TargetPath = Join-Path $Root "START.bat"
  $sc.WorkingDirectory = $Root
  $sc.Description = "GGUF Runner — Mehdi Tariri"
  $ico = Join-Path $Root "installer\assets\app.ico"
  if (Test-Path $ico) { $sc.IconLocation = "$ico,0" }
  $sc.Save()
  Write-Host "[OK] Desktop shortcut created"
} catch {}

$models = @(Get-ChildItem (Join-Path $Root "models\*.gguf") -EA SilentlyContinue).Count
if ($models -eq 0) { Write-Host "[!] Add .gguf files to models\" } else { Write-Host "[OK] $models model(s)" }

Write-Host ""
Write-Host "Setup finished for $winLabel ($bits-bit)."
Write-Host ""
