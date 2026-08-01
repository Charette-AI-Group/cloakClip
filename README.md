# CloakClip

Encrypt ("cloak") and decrypt ("uncloak") text with a shared password — a friendly GUI replacement for the original `encrypt.ps1` / `decrypt.ps1` PowerShell scripts.

## Usage

Anything you copy appears in the top box automatically, unless you are typing in it. You can also type straight into the box, or fill it with **Paste**.

**To protect text:** put it in the top box, enter the password, click **Cloak**. The encrypted string appears in **Result** and is copied to the clipboard, ready to paste.

**To read protected text:** copy the encrypted string, enter the same password, click **Uncloak**. The original text appears in **Result** — on screen only. Click **Copy** if you actually need to paste it somewhere.

A wrong password, or text that was not encrypted, shows a message in the status bar and changes nothing.

**Clear Clipboard & History** empties the clipboard and purges Windows clipboard history (Win+V), which is the way to clean up plain text that *other* apps copied — for example the password you copied out of an email in order to cloak it. Items you pinned in Win+V are kept.

## How your secrets are protected

Windows keeps a history of everything copied (Win+V) and can sync it to the cloud, so a decrypted secret sitting on the clipboard normally outlives both the paste and the app. CloakClip avoids that three ways:

- **Uncloaking does not touch the clipboard.** The plain text is only displayed. If you just need to read a message, it never leaves the window.
- **When you do click Copy, the text is marked secret** using the same Windows clipboard formats password managers use, so Windows keeps it out of clipboard history and cloud sync. It still pastes normally.
- **Closing the app clears a copied secret** from the clipboard. Cloaked text is left alone, since it is encrypted and you may still want to paste it.

## Compatibility

The scheme is identical to the PowerShell scripts (AES-256-CBC, key = SHA-256 of the password, random 16-byte IV prepended, Base64): strings encrypted by either tool decrypt in the other. As with the scripts, the key derivation is a single unsalted SHA-256 — use a long password.

## One-time setup

```powershell
cd W:\projects\26cloakClip
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
```

## Daily workflow

```powershell
cd W:\projects\26cloakClip
.\.venv\Scripts\Activate.ps1
cloak-clip
```

Or without the script entry point:

```powershell
python -m cloakClip.main
```

Or just double-click **`runApp.cmd`** in the project folder (needs the one-time setup done first).

## Tests and lint

```powershell
pytest
ruff check src tests
```

## Structure

| Layer | Folder | Purpose |
|-------|--------|---------|
| Entry | `src/cloakClip/main.py` | Start `QApplication`, show main window |
| Config | `src/cloakClip/appConfig.py` | Paths, defaults, app metadata |
| UI | `src/cloakClip/ui/` | Widgets and dialogs only |
| Services | `src/cloakClip/services/` | Business logic (no Qt widgets) |
| Models | `src/cloakClip/models/` | Plain Python data types |

See `AGENTS.md` for architecture and naming conventions (for you and AI agents).

---
*Created from the Qt App Template.*
