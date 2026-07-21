#define MyAppName "TCG Image Processor"
#define MyAppVersion "1.0.0-rc1"
#define MyAppPublisher "TCG Image Processor"
#define MyAppExeName "TCG Image Processor.exe"

[Setup]
AppId={{8EE0AB9A-0D1F-4DE4-9A92-9BFD145A43DF}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\TCG Image Processor
DefaultGroupName=TCG Image Processor
OutputDir=output
OutputBaseFilename=TCG-Image-Processor-Setup-1.0.0-rc1
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\{#MyAppExeName}

[Files]
Source: "..\dist\TCG Image Processor\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\TCG Image Processor"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\TCG Image Processor"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Desktop-Verknüpfung erstellen"; GroupDescription: "Zusätzliche Verknüpfungen:"

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "TCG Image Processor starten"; Flags: nowait postinstall skipifsilent
