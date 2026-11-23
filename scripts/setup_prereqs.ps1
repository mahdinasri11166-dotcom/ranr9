# Compatibility wrapper — full logic is in detect_and_setup.ps1
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
& powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $here "detect_and_setup.ps1")
