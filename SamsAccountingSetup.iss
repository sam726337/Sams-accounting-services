[Setup]
AppId={{6F1B60E7-1E58-4E30-8B54-80D4AC86E211}
AppName=Sams Accounting Desktop
AppVersion=1.0.3
AppPublisher=The Jishu IT Solution
DefaultDirName={autopf}\Sams Accounting Desktop
DefaultGroupName=Sams Accounting Desktop
DisableProgramGroupPage=yes
OutputDir=installer-output-1.0.3-r4
OutputBaseFilename=SamsAccountingSetup-1.0.3
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayName=Sams Accounting Desktop
VersionInfoVersion=1.0.3.0
VersionInfoCompany=The Jishu IT Solution
VersionInfoDescription=Sams Accounting Desktop Setup
VersionInfoProductName=Sams Accounting Desktop
LicenseFile=TERMS.txt
InfoBeforeFile=PRIVACY.txt

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "release-1.0.3-r3\SamsAccountingDesktop\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Sams Accounting Desktop"; Filename: "{app}\SamsAccountingDesktop.exe"
Name: "{autodesktop}\Sams Accounting Desktop"; Filename: "{app}\SamsAccountingDesktop.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\SamsAccountingDesktop.exe"; Description: "{cm:LaunchProgram,Sams Accounting Desktop}"; Flags: nowait postinstall skipifsilent
