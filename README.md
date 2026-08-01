# CloakClip

Encrypt ("cloak") and decrypt ("uncloak") the text in the Windows clipboard with a shared password — a friendly GUI replacement for the original `encrypt.ps1` / `decrypt.ps1` PowerShell scripts.

## Usage

1. Copy any text (Ctrl+C) — it appears in the clipboard preview.
2. Type the shared password.
3. Click **Cloak Clipboard** — the clipboard now holds an encrypted Base64 string; paste it anywhere.
4. To read one: copy the encrypted string, enter the same password, click **Uncloak Clipboard**, then paste the plain text.
5. **Clear Clipboard** wipes the clipboard after you are done pasting sensitive text.

A wrong password (or non-encrypted clipboard text) shows a message in the status bar and leaves the clipboard untouched.

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
