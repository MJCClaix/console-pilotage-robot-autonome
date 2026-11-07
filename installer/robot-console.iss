; Installeur Windows de la console de pilotage du robot (Inno Setup 6).
;
; Prérequis : avoir construit les exécutables avec `build_exes.py` (dossier dist\).
; Compilation, depuis PowerShell à la racine du projet :
;   & "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer\robot-console.iss
; Le setup est créé dans installer\Output\robot-console-setup.exe.
;
; Installation par utilisateur, sans droits administrateur, dans %LOCALAPPDATA%\Programs.

#define AppName "Console de pilotage du robot"
#define AppVersion "0.1.0"

[Setup]
ChangesEnvironment=yes
AppId={{BDD0EEB8-E7BE-487A-8D7D-EABE82B730B0}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher=Club robotique
DefaultDirName={autopf}\RobotConsole
DefaultGroupName=Pilotage du robot
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=Output
OutputBaseFilename=robot-console-setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
UninstallDisplayName={#AppName}

[Languages]
Name: "french"; MessagesFile: "compiler:Languages\French.isl"

[Tasks]
Name: "autostart"; Description: "Lancer la Console de pilotage au démarrage de Windows"; GroupDescription: "Options :"
Name: "desktopicon"; Description: "Créer un raccourci de l'interface de pilotage sur le Bureau"; GroupDescription: "Options :"

[InstallDelete]
; Anciens noms (versions précédentes de l'installeur)
Type: files; Name: "{app}\robot-cli.exe"
Type: files; Name: "{app}\robot-web.exe"

[Files]
Source: "..\dist\console-pilotage.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\dist\interface-pilotage.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\Interface de pilotage"; Filename: "{app}\interface-pilotage.exe"; WorkingDir: "{app}"
Name: "{group}\Console de pilotage"; Filename: "{app}\console-pilotage.exe"; WorkingDir: "{app}"
Name: "{userstartup}\Console de pilotage"; Filename: "{app}\console-pilotage.exe"; WorkingDir: "{app}"; Tasks: autostart
Name: "{userdesktop}\Interface de pilotage"; Filename: "{app}\interface-pilotage.exe"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\interface-pilotage.exe"; Description: "Lancer l'interface de pilotage"; WorkingDir: "{app}"; Flags: nowait postinstall skipifsilent

[Code]
// Ajoute le dossier d'installation au PATH de l'utilisateur, pour lancer
// `console-pilotage` depuis n'importe quel terminal.

function PathContains(Path, Dir: string): Boolean;
begin
  Result := Pos(';' + Uppercase(Dir) + ';', ';' + Uppercase(Path) + ';') > 0;
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  Path: string;
  AppDir: string;
begin
  if CurStep = ssPostInstall then
  begin
    AppDir := ExpandConstant('{app}');
    if not RegQueryStringValue(HKCU, 'Environment', 'Path', Path) then
      Path := '';
    if not PathContains(Path, AppDir) then
    begin
      if Path = '' then
        Path := AppDir
      else
        Path := Path + ';' + AppDir;
      RegWriteExpandStringValue(HKCU, 'Environment', 'Path', Path);
    end;
  end;
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  Path: string;
  AppDir: string;
begin
  if CurUninstallStep = usPostUninstall then
  begin
    AppDir := ExpandConstant('{app}');
    if RegQueryStringValue(HKCU, 'Environment', 'Path', Path) then
    begin
      StringChangeEx(Path, ';' + AppDir, '', True);
      StringChangeEx(Path, AppDir + ';', '', True);
      StringChangeEx(Path, AppDir, '', True);
      RegWriteExpandStringValue(HKCU, 'Environment', 'Path', Path);
    end;
  end;
end;
