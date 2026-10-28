; Сборка: ISCC /DAppVersion=0.1.0 packaging\windows\CyberLab.iss
#ifndef AppVersion
  #define AppVersion "0.1.0"
#endif

[Setup]
AppId={{848DC1EE-0DFB-4F4D-86C6-847963F0D78A}
AppName=CYBERLAB
AppVersion={#AppVersion}
AppPublisher=CYBERLAB
AppPublisherURL=https://github.com/kiollaif/cyberlab
DefaultDirName={localappdata}\Programs\CyberLab
DefaultGroupName=CYBERLAB
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0.17763
OutputDir=..\..\dist\desktop
OutputBaseFilename=CyberLab-Setup
SetupIconFile=..\..\src\cyberlab\resources\cyberlab.ico
UninstallDisplayIcon={app}\CyberLab.exe
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
CloseApplications=yes

[Languages]
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"

[Files]
Source: "..\..\dist\frozen\CyberLab.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{userprograms}\CYBERLAB\CYBERLAB"; Filename: "{app}\CyberLab.exe"
Name: "{userdesktop}\CYBERLAB"; Filename: "{app}\CyberLab.exe"

[Run]
Filename: "{app}\CyberLab.exe"; Description: "Запустить CYBERLAB"; Flags: nowait postinstall skipifsilent

; Пользовательская история находится вне {app}. Удаление программы её не удаляет.
