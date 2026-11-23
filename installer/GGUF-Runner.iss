; GGUF Runner Setup — builds GGUF-Runner-Setup.exe
; Compile with Inno Setup 6 (GitHub Actions or local)
; Author: Mehdi Tariri <mahditariri@gmail.com>

#define MyAppName "GGUF Runner"
#define MyAppVersion "3.5.0"
#define MyAppPublisher "Mehdi Tariri"
#define MyAppURL "https://github.com/mahditariri/GGUF-Runner"
#define MyAppExeName "START.bat"

[Setup]
AppId={{8F3C2A91-4B67-4E2D-9C11-A1B2C3D4E5F6}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
DefaultDirName={localappdata}\GGUF-Runner
DefaultGroupName=GGUF Runner
DisableProgramGroupPage=no
LicenseFile=..\LICENSE
OutputDir=Output
OutputBaseFilename=GGUF-Runner-Setup-{#MyAppVersion}
SetupIconFile=assets\app.ico
UninstallDisplayIcon={app}\installer\assets\app.ico
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible
ArchitecturesAllowed=x86 x64compatible
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
InfoBeforeFile=INFO_BEFORE.txt
InfoAfterFile=INFO_AFTER.txt
MinVersion=6.1
CloseApplications=no

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop icon"; GroupDescription: "Icons:"; Flags: checkedonce
Name: "autorunsetup"; Description: "After install, detect Windows and download llama-server"; Flags: checkedonce

[Files]
Source: "..\START.bat"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\SETUP.bat"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\GGUF-Runner.bat"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\start.bat"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\start_multi.bat"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\stop.bat"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\settings.bat"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\install.bat"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\uninstall.bat"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\bootstrap.bat"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\FirstRun.bat"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\config.ini"; DestDir: "{app}"; Flags: onlyifdoesntexist
Source: "..\README.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\LICENSE"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\web\*"; DestDir: "{app}\web"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\scripts\*"; DestDir: "{app}\scripts"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\docs\*"; DestDir: "{app}\docs"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\profiles\*"; DestDir: "{app}\profiles"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\books\README.txt"; DestDir: "{app}\books"; Flags: ignoreversion
Source: "..\memory\README.txt"; DestDir: "{app}\memory"; Flags: ignoreversion
Source: "..\dataset\README.txt"; DestDir: "{app}\dataset"; Flags: ignoreversion
Source: "..\workspace\README.txt"; DestDir: "{app}\workspace"; Flags: ignoreversion
Source: "assets\app.ico"; DestDir: "{app}\installer\assets"; Flags: ignoreversion
Source: "INFO_BEFORE.txt"; DestDir: "{app}\installer"; Flags: ignoreversion
Source: "INFO_AFTER.txt"; DestDir: "{app}\installer"; Flags: ignoreversion

[Dirs]
Name: "{app}\bin"
Name: "{app}\models"
Name: "{app}\books"
Name: "{app}\memory"
Name: "{app}\memory\vectors"
Name: "{app}\dataset"
Name: "{app}\dataset\auto"
Name: "{app}\sessions"
Name: "{app}\workspace"

[Icons]
Name: "{group}\GGUF Runner"; Filename: "{app}\START.bat"; WorkingDir: "{app}"; IconFilename: "{app}\installer\assets\app.ico"
Name: "{group}\Setup / Update prereqs"; Filename: "{app}\SETUP.bat"; WorkingDir: "{app}"; IconFilename: "{app}\installer\assets\app.ico"
Name: "{group}\Uninstall"; Filename: "{uninstallexe}"
Name: "{autodesktop}\GGUF Runner"; Filename: "{app}\START.bat"; WorkingDir: "{app}"; IconFilename: "{app}\installer\assets\app.ico"; Tasks: desktopicon

[Run]
Filename: "powershell.exe"; Parameters: "-NoProfile -ExecutionPolicy Bypass -File ""{app}\scripts\detect_and_setup.ps1"""; WorkingDir: "{app}"; StatusMsg: "Detecting Windows and downloading llama-server..."; Flags: runhidden waituntilterminated; Tasks: autorunsetup
Filename: "{app}\START.bat"; Description: "Launch GGUF Runner now"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}\memory\proxy_cache"
Type: filesandordirs; Name: "{app}\bin\_download_tmp"
