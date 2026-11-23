; GGUF Runner NSIS Installer
; Developer: Mehdi Tariri <mahditariri@gmail.com>
; Build: makensis GGUF-Runner.nsi

!define APP_NAME "GGUF Runner"
!define APP_VERSION "4.9.2"
!define APP_PUBLISHER "Timi Tosee No / Mehdi Tariri & Mohsen Tarifii"
!define APP_URL "https://github.com/mahditariri/GGUF-Runner"
!define APP_DIR "GGUF-Runner"

Name "${APP_NAME}"
OutFile "Output\GGUF-Runner-Setup-${APP_VERSION}.exe"
InstallDir "$LOCALAPPDATA\${APP_DIR}"
InstallDirRegKey HKCU "Software\${APP_PUBLISHER}\${APP_NAME}" "InstallDir"
RequestExecutionLevel user
SetCompressor /SOLID lzma
Unicode true

; Modern UI
!include "MUI2.nsh"
!include "x64.nsh"
!include "LogicLib.nsh"
!include "WinVer.nsh"

!define MUI_ABORTWARNING
!define MUI_ICON "assets\app.ico"
!define MUI_UNICON "assets\app.ico"
!define MUI_WELCOMEPAGE_TITLE "${APP_NAME} ${APP_VERSION}"
!define MUI_WELCOMEPAGE_TEXT "Team: Mehdi Tariri (mahditariri@gmail.com) · Mohsen Tarifii (Masean.us@gmail.com)$\r$\n$\r$\nOffline-ready install: embedded Python + llama-cpp-python + llama-server. Add .gguf models after install."

!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_LICENSE "..\LICENSE"
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_COMPONENTS
!insertmacro MUI_PAGE_INSTFILES
!define MUI_FINISHPAGE_RUN "$INSTDIR\RUN_GUI.bat"
!define MUI_FINISHPAGE_RUN_TEXT "First Run / تشخیص ویندوز و اجرا"
!define MUI_FINISHPAGE_SHOWREADME "$INSTDIR\docs\INSTALL_WINDOWS.md"
!define MUI_FINISHPAGE_SHOWREADME_TEXT "Windows install guide"
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

!insertmacro MUI_LANGUAGE "English"

Var OSLabel
Var BitsLabel

Section "GGUF Runner (required)" SecMain
  SectionIn RO
  SetOutPath "$INSTDIR"

  ; Detect OS for display / log
  ${If} ${IsWin7}
    StrCpy $OSLabel "Windows 7"
  ${ElseIf} ${IsWin8}
    StrCpy $OSLabel "Windows 8"
  ${ElseIf} ${IsWin8.1}
    StrCpy $OSLabel "Windows 8.1"
  ${ElseIf} ${IsWin10}
    StrCpy $OSLabel "Windows 10/11"
  ${Else}
    StrCpy $OSLabel "Windows"
  ${EndIf}

  ${If} ${RunningX64}
    StrCpy $BitsLabel "64-bit"
  ${Else}
    StrCpy $BitsLabel "32-bit"
  ${EndIf}

  DetailPrint "Detected: $OSLabel ($BitsLabel)"

  ; App files
  File "..\START.bat"
  File "..\CHAT.bat"
  File "..\RUN_GUI.bat"
  File /nonfatal "..\INSTALL.bat"
  File /nonfatal "..\نصب.txt"
  File "..\SETUP.bat"
  File "..\GGUF-Runner.bat"
  File "..\start.bat"
  File "..\start_multi.bat"
  File "..\stop.bat"
  File "..\settings.bat"
  File "..\install.bat"
  File "..\uninstall.bat"
  File "..\bootstrap.bat"
  File "..\FirstRun.bat"
  File "..\config.ini"
  File /nonfatal "..\version.json"
  File "..\README.md"
  File "..\LICENSE"
  File /nonfatal "..\requirements.txt"
  File /nonfatal "..\PUBLISH_GITHUB.md"

  SetOutPath "$INSTDIR\web"
  File /r "..\web\*.*"

  SetOutPath "$INSTDIR\scripts"
  File /r "..\scripts\*.*"

  SetOutPath "$INSTDIR\docs"
  File /r "..\docs\*.*"

  SetOutPath "$INSTDIR\profiles"
  File /r "..\profiles\*.*"
  SetOutPath "$INSTDIR\profiles\argos_packages"
  File /nonfatal /r "..\profiles\argos_packages\*.*"

  SetOutPath "$INSTDIR\installer\assets"
  File "assets\app.ico"

  ; Do NOT File /r payload\*.* — that would duplicate python trees and blow NSIS >2GB mmap limit.
  ; Offline Python 3.11 (Win10/11)
  SetOutPath "$INSTDIR\python"
  File /r "payload\python-offline-amd64\*.*"

  ; Offline Python 3.8 (Win7) + tkinter injected in CI
  SetOutPath "$INSTDIR\python38"
  File /r "payload\python-offline-win7-amd64\*.*"


  ; llama-server + DLLs from CI
  SetOutPath "$INSTDIR\bin"
  File /nonfatal /r "..\bin\*.*"

  ; data folders
  CreateDirectory "$INSTDIR\bin"
  CreateDirectory "$INSTDIR\models"
  CreateDirectory "$INSTDIR\books"
  CreateDirectory "$INSTDIR\memory"
  CreateDirectory "$INSTDIR\memory\vectors"
  CreateDirectory "$INSTDIR\dataset"
  CreateDirectory "$INSTDIR\dataset\auto"
  CreateDirectory "$INSTDIR\sessions"
  CreateDirectory "$INSTDIR\workspace"

  ; README stubs if present
  SetOutPath "$INSTDIR\books"
  File /nonfatal "..\books\README.txt"
  SetOutPath "$INSTDIR\memory"
  File /nonfatal "..\memory\README.txt"
  SetOutPath "$INSTDIR\dataset"
  File /nonfatal "..\dataset\README.txt"
  SetOutPath "$INSTDIR\workspace"
  File /nonfatal "..\workspace\README.txt"
  SetOutPath "$INSTDIR\workspace\user_tools"
  File /nonfatal /r "..\workspace\user_tools\*.*"
  SetOutPath "$INSTDIR\workspace\plugins"
  File /nonfatal /r "..\workspace\plugins\*.*"
  File /nonfatal "..\workspace\proxies.json"

  ; Detect Windows and choose Python (3.8 vs 3.11)
  DetailPrint "Detecting Windows version..."
  nsExec::ExecToLog '"$INSTDIR\scripts\install_detect_windows.bat"'
  ExecWait '"$INSTDIR\scripts\install_detect_windows.bat"' $0
  DetailPrint "install_detect_windows exit=$0"
  IfFileExists "$INSTDIR\profiles\os_class.txt" 0 +2
    DetailPrint "Wrote profiles\os_class.txt"

  ; Write detection log
  FileOpen $0 "$INSTDIR\installer\detect_log.txt" w
  FileWrite $0 "OS=$OSLabel$\r$\nBits=$BitsLabel$\r$\nInstallDir=$INSTDIR$\r$\nPublisher=${APP_PUBLISHER}$\r$\n"
  FileClose $0

  ; Registry + uninstaller
  WriteRegStr HKCU "Software\${APP_PUBLISHER}\${APP_NAME}" "InstallDir" "$INSTDIR"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" "DisplayName" "${APP_NAME}"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" "UninstallString" "$\"$INSTDIR\Uninstall.exe$\""
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" "DisplayIcon" "$INSTDIR\installer\assets\app.ico"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" "Publisher" "${APP_PUBLISHER}"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" "DisplayVersion" "${APP_VERSION}"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" "URLInfoAbout" "${APP_URL}"
  WriteUninstaller "$INSTDIR\Uninstall.exe"
SectionEnd

Section "Desktop icon" SecDesktop
  SectionIn 1
  CreateShortcut "$DESKTOP\${APP_NAME}.lnk" "$INSTDIR\RUN_GUI.bat" "" "$INSTDIR\installer\assets\app.ico" 0
SectionEnd

Section "Start Menu shortcuts" SecStart
  SectionIn 1
  CreateDirectory "$SMPROGRAMS\${APP_NAME}"
  CreateShortcut "$SMPROGRAMS\${APP_NAME}\${APP_NAME}.lnk" "$INSTDIR\RUN_GUI.bat" "" "$INSTDIR\installer\assets\app.ico" 0
  CreateShortcut "$SMPROGRAMS\${APP_NAME}\Setup prereqs.lnk" "$INSTDIR\SETUP.bat" "" "$INSTDIR\installer\assets\app.ico" 0
  CreateShortcut "$SMPROGRAMS\${APP_NAME}\Uninstall.lnk" "$INSTDIR\Uninstall.exe"
SectionEnd

Section /o "Optional online update (internet)" SecPrereq
  DetailPrint "Running detect_and_setup.ps1 for $OSLabel $BitsLabel ..."
  ; nsExec plugin not always present — use ExecWait
  ExecWait 'powershell -NoProfile -ExecutionPolicy Bypass -File "$INSTDIR\scripts\detect_and_setup.ps1"' $0
  DetailPrint "Setup exit code: $0"
SectionEnd

Section "Uninstall"
  Delete "$DESKTOP\${APP_NAME}.lnk"
  RMDir /r "$SMPROGRAMS\${APP_NAME}"
  Delete "$INSTDIR\Uninstall.exe"
  RMDir /r "$INSTDIR\web"
  RMDir /r "$INSTDIR\scripts"
  RMDir /r "$INSTDIR\docs"
  RMDir /r "$INSTDIR\profiles"
  RMDir /r "$INSTDIR\installer"
  ; keep models/bin user data by default — remove only app scripts
  Delete "$INSTDIR\START.bat"
  Delete "$INSTDIR\SETUP.bat"
  Delete "$INSTDIR\GGUF-Runner.bat"
  Delete "$INSTDIR\start.bat"
  Delete "$INSTDIR\start_multi.bat"
  Delete "$INSTDIR\stop.bat"
  Delete "$INSTDIR\settings.bat"
  Delete "$INSTDIR\install.bat"
  Delete "$INSTDIR\uninstall.bat"
  Delete "$INSTDIR\bootstrap.bat"
  Delete "$INSTDIR\FirstRun.bat"
  Delete "$INSTDIR\config.ini"
  Delete "$INSTDIR\README.md"
  Delete "$INSTDIR\LICENSE"
  DeleteRegKey HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}"
  DeleteRegKey HKCU "Software\${APP_PUBLISHER}\${APP_NAME}"
  RMDir "$INSTDIR"
SectionEnd

; Section descriptions
LangString DESC_SecMain ${LANG_ENGLISH} "Core application files"
LangString DESC_SecDesktop ${LANG_ENGLISH} "Create desktop icon"
LangString DESC_SecStart ${LANG_ENGLISH} "Start Menu shortcuts"
LangString DESC_SecPrereq ${LANG_ENGLISH} "Optional: download updates if offline Python missing (needs internet). Default OFF."

!insertmacro MUI_FUNCTION_DESCRIPTION_BEGIN
  !insertmacro MUI_DESCRIPTION_TEXT ${SecMain} $(DESC_SecMain)
  !insertmacro MUI_DESCRIPTION_TEXT ${SecDesktop} $(DESC_SecDesktop)
  !insertmacro MUI_DESCRIPTION_TEXT ${SecStart} $(DESC_SecStart)
  !insertmacro MUI_DESCRIPTION_TEXT ${SecPrereq} $(DESC_SecPrereq)
!insertmacro MUI_FUNCTION_DESCRIPTION_END
