; VenueView Windows installer definition.
; Build the one-folder bundle first, then run build_installer_windows.ps1 on
; Windows with Inno Setup installed. Do not place private calendars in dist/.

#define MyAppName "VenueView"
#ifndef MyAppVersion
  #error MyAppVersion must be supplied by build_installer_windows.ps1
#endif
#define MyAppPublisher "VenueView"
#define MyAppExeName "VenueView.exe"
#ifndef MyAppFileSuffix
  #define MyAppFileSuffix ""
#endif
#ifndef MyOutputDir
  #define MyOutputDir "..\..\dist\installer"
#endif

[Setup]
AppId={{B28E0D4D-8C58-4B4C-8D0C-5C7E8B2D4E40}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
UninstallDisplayName={#MyAppName}
DefaultDirName={localappdata}\Programs\VenueView
DefaultGroupName=VenueView
DisableProgramGroupPage=yes
OutputDir={#MyOutputDir}
OutputBaseFilename=VenueView-{#MyAppVersion}{#MyAppFileSuffix}-Windows-x64-Setup
Compression=lzma2
SolidCompression=yes
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=lowest
WizardStyle=modern
CloseApplications=yes
RestartApplications=no
SetupIconFile=..\assets\venueview.ico
UninstallDisplayIcon={app}\{#MyAppExeName}

[Files]
Source: "..\..\dist\VenueView\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\VenueView"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\VenueView"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: unchecked

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch VenueView"; Flags: nowait postinstall skipifsilent

[Code]
procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  SettingsFile: String;
  SettingsDirectory: String;
begin
  if CurUninstallStep <> usUninstall then
    exit;

  if SuppressibleMsgBox(
       'Remove the imported VenueView organization settings from this Windows account too?' + #13#10 + #13#10 +
       'Choose No to preserve them for a future VenueView installation.',
       mbConfirmation, MB_YESNO, IDNO) = IDYES then
  begin
    SettingsDirectory := ExpandConstant('{userappdata}\VenueView');
    SettingsFile := SettingsDirectory + '\private_rules.json';
    DeleteFile(SettingsFile);
    RemoveDir(SettingsDirectory);
  end;
end;
