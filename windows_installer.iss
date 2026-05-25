#define AppName "Slay the Spire 2 Drawer"
#define AppVersion "0.0.1-alpha"
#define AppPublisher "qTp_meteor"

#define AppExeName AppName + ".exe"
#define AppSetupName AppName + "Setup"

#define SourceDir "./dist/Slay the Spire 2 Drawer/"
#define IconFile "./app/resources/images/icon.ico"

[Setup]
AppId={{0d77c066-4f95-4313-ad67-9541a1483e71}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
AppVerName={#AppName} {#AppVersion}
DefaultDirName={pf}\{#AppName}
DefaultGroupName={#AppName}
Compression=lzma
SolidCompression=yes
OutputBaseFilename={#AppSetupName}-{#AppVersion}
OutputDir=WinInstallerOutput
ArchitecturesInstallIn64BitMode=x64
Uninstallable=yes
SetupIconFile={#IconFile}
UninstallDisplayIcon={app}\{#AppExeName}

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Files]
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExeName}"; WorkingDir: "{app}"
Name: "{commondesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; WorkingDir: "{app}"

[Run]
Filename: "{app}\{#AppExeName}"; Description: "Launch {#AppName}"; Flags: nowait postinstall skipifsilent

[Code]
// Show a message when upgrading from a previous version
function InitializeSetup(): Boolean;
var
  PrevVersion: String;
begin
  // Check if previous version is installed
  if RegQueryStringValue(HKLM, 'Software\Microsoft\Windows\CurrentVersion\Uninstall\{0d77c066-4f95-4313-ad67-9541a1483e71}_is1', 'DisplayVersion', PrevVersion) then
  begin
    if MsgBox('A previous version of ' + '{#AppName}' + ' (' + PrevVersion + ') is already installed.'#13#13 +
      'Do you want to upgrade to version {#AppVersion}?', mbConfirmation, MB_YESNO) = IDNO then
    begin
      Result := False;
      Exit;
    end;
  end;
  Result := True;
end;