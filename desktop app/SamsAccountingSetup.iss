[Setup]
AppId={{6F1B60E7-1E58-4E30-8B54-80D4AC86E211}
AppName=Sams Accounting Desktop
AppVersion=1.0.2
AppPublisher=Sams IT Solution
DefaultDirName={autopf}\Sams Accounting Desktop
DefaultGroupName=Sams Accounting Desktop
DisableProgramGroupPage=yes
OutputDir=installer-output
OutputBaseFilename=SamsAccountingSetup-1.0.2
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64
UninstallDisplayName=Sams Accounting Desktop
VersionInfoVersion=1.0.2.0
VersionInfoCompany=Sams IT Solution
VersionInfoDescription=Sams Accounting Desktop Setup
VersionInfoProductName=Sams Accounting Desktop

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "dist\SamsAccountingDesktop\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Sams Accounting Desktop"; Filename: "{app}\SamsAccountingDesktop.exe"
Name: "{autodesktop}\Sams Accounting Desktop"; Filename: "{app}\SamsAccountingDesktop.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\SamsAccountingDesktop.exe"; Description: "{cm:LaunchProgram,Sams Accounting Desktop}"; Flags: nowait postinstall skipifsilent
