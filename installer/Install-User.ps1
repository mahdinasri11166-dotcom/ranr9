# Portable "installer" without Inno Setup
# Run: Right-click > Run with PowerShell
# Or: powershell -ExecutionPolicy Bypass -File Install-User.ps1
# Author: Mehdi Tariri <mahditariri@gmail.com>

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
if (-not (Test-Path (Join-Path $Root "GGUF-Runner.bat"))) {
  $Root = $PSScriptRoot
  if (-not (Test-Path (Join-Path $Root "GGUF-Runner.bat"))) {
    $Root = Get-Location
  }
}

$Target = Join-Path $env:LOCALAPPDATA "GGUF-Runner"
Write-Host "Installing to $Target"
New-Item -ItemType Directory -Force -Path $Target | Out-Null

# Copy project files
$exclude = @(".git", "installer\Output")
Get-ChildItem -Path $Root -Force | ForEach-Object {
  if ($_.Name -eq ".git") { return }
  Copy-Item -Path $_.FullName -Destination (Join-Path $Target $_.Name) -Recurse -Force
}

foreach ($d in @("bin","models","books","memory","dataset","sessions","workspace")) {
  New-Item -ItemType Directory -Force -Path (Join-Path $Target $d) | Out-Null
}

# Shortcuts
$Wsh = New-Object -ComObject WScript.Shell
$Desktop = [Environment]::GetFolderPath("Desktop")
$Start = Join-Path ([Environment]::GetFolderPath("StartMenu")) "Programs\GGUF Runner"
New-Item -ItemType Directory -Force -Path $Start | Out-Null

$sc1 = $Wsh.CreateShortcut((Join-Path $Desktop "GGUF Runner.lnk"))
$sc1.TargetPath = Join-Path $Target "GGUF-Runner.bat"
$sc1.WorkingDirectory = $Target
$sc1.Save()

$sc2 = $Wsh.CreateShortcut((Join-Path $Start "GGUF Runner.lnk"))
$sc2.TargetPath = Join-Path $Target "GGUF-Runner.bat"
$sc2.WorkingDirectory = $Target
$sc2.Save()

$sc3 = $Wsh.CreateShortcut((Join-Path $Start "First Run Setup.lnk"))
$sc3.TargetPath = Join-Path $Target "FirstRun.bat"
$sc3.WorkingDirectory = $Target
$sc3.Save()

Write-Host ""
Write-Host "Done. Desktop shortcut created."
Write-Host "Next: put llama-server.exe in $Target\bin"
Write-Host "      put .gguf models in $Target\models"
Write-Host "Developer: Mehdi Tariri - mahditariri@gmail.com"
Start-Process (Join-Path $Target "bootstrap.bat")
