; Installer for CloakClip. Built with Inno Setup 6:
;
;     ISCC.exe installer\cloakClip.iss
;
; It expects dist\CloakClip\ to exist - the folder bundle, not the one-file
; exe. tools\buildInstaller.py builds that, self-tests it, and passes the
; version in from appConfig, so the installer, the About box and the wheel
; cannot disagree about what this is; the default below is only what a bare
; ISCC run would use.
;
; Why an installer at all, when CloakClip.exe already runs on its own: a
; single file has no Start menu entry, no way to remove it from Add or Remove
; Programs, and unpacks itself to a temp folder on every launch. The one-file
; exe stays on the release for anyone who prefers it - a copy on a USB stick
; is a real use.
;
; Per-user by design. CloakClip writes only to APPDATA, and asking for
; administrator rights to install a clipboard tool is how a small utility
; becomes a thing IT has to approve.

#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif

#define AppName "CloakClip"
#define Publisher "Charette AI Group, LLC"
#define SiteUrl "https://charette-ai-group.github.io/cloakClip/"
#define RepoUrl "https://github.com/Charette-AI-Group/cloakClip"
#define ExeName "CloakClip.exe"
#define BundleDir "..\dist\CloakClip"

[Setup]
; Fixed for the life of the application: this is what lets an upgrade replace
; an install rather than sit beside it, and what the uninstaller is found by.
; Never regenerate it.
AppId={{2CB19076-8AE6-4D05-8FAA-BA04AB72699E}
AppName={#AppName}
AppVersion={#AppVersion}
VersionInfoVersion={#AppVersion}
AppPublisher={#Publisher}
AppPublisherURL={#SiteUrl}
AppSupportURL={#RepoUrl}/issues
AppUpdatesURL={#RepoUrl}/releases
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
SetupIconFile=..\src\cloakClip\resources\cloakClip.ico
UninstallDisplayIcon={app}\{#ExeName}
UninstallDisplayName={#AppName}
OutputDir=..\dist
OutputBaseFilename=CloakClipSetup-{#AppVersion}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
; Per-user, so there is no UAC prompt and no Program Files. With
; PrivilegesRequired=lowest, {autopf} resolves to the user's own programs
; folder rather than C:\Program Files.
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
; Shown on the first page, so the licence is read before anything is written.
LicenseFile=..\LICENSE

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Shortcuts:"

[Files]
Source: "{#BundleDir}\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#ExeName}"
Name: "{group}\Uninstall {#AppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#ExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#ExeName}"; Description: "Start {#AppName}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; The bundle only. Deliberately not APPDATA\CloakClip: an uninstall that
; silently discards somebody's window position and theme is a surprise, and a
; reinstall is the commonest reason to uninstall. The remembered passwords
; there are DPAPI-encrypted to the Windows account, and anyone who wants them
; gone has Password > Clear Password History, which says exactly what it does.
Type: filesandordirs; Name: "{app}\_internal"

[Code]
{ A running copy holds its own files open, so replacing them mid-upgrade
  fails with a message about a file in use that says nothing about why. Ask
  first instead, in words that name the application. The main window's title
  is exactly the application name (appConfig.windowTitle).

  Asking the person to close it, rather than letting Restart Manager do it
  (CloseApplications), is deliberate: closing CloakClip through its own
  window runs its exit sweep of the clipboard and clipboard history.

  SuppressibleMsgBox, not MsgBox: a plain MsgBox still appears under
  /SUPPRESSMSGBOXES and would hang a silent install. Silently, the answer is
  No - abort cleanly rather than fail halfway on a file in use. }
function InitializeSetup(): Boolean;
var
  WindowHandle: HWND;
begin
  Result := True;
  WindowHandle := FindWindowByWindowName('{#AppName}');
  if WindowHandle <> 0 then
    Result := SuppressibleMsgBox(
      '{#AppName} appears to be running.' + #13#10#13#10 +
      'Close it before continuing, or setup cannot replace its files.' + #13#10#13#10 +
      'Continue anyway?',
      mbConfirmation, MB_YESNO, IDNO) = IDYES;
end;
