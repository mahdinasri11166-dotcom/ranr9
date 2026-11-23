# Installer EXE (NSIS) — v2.4

Built by GitHub Actions workflow **Build NSIS Setup EXE**.

## What is inside

- Application scripts (Desktop Chat, Agent, OSINT)
- Embedded Python 3.11 amd64 under `python\`
- Packages: `llama-cpp-python`, `customtkinter`, `requests`, `pypdf`, `Pillow`, `numpy`
- `bin\llama-server.exe` (CPU x64) when CI download succeeds
- Marker `python\gguf_runner_offline.json` when stack verified

## Build policy (hardened)

CI **fails** if:

- `llama-cpp-python` cannot be installed or imported
- `customtkinter` (or other core packages) cannot import
- `llama-server.exe` was not downloaded
- NSIS did not produce the Setup EXE

So a published Setup from a **green** Actions run is expected to work offline for Desktop Chat after you add models.

## After install

1. Copy `.gguf` files into `models\`
2. Run `CHAT.bat` (or Finish → First Run)
3. OSINT network tools still need internet when used

## If chat still cannot load models

Run `SETUP.bat` once with internet, then `scripts\doctor.bat`.
