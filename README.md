# CloakClip

Encrypt ("cloak") and decrypt ("uncloak") text with a shared password — a friendly GUI replacement for the original `encrypt.ps1` / `decrypt.ps1` PowerShell scripts.

## Usage

The window has two tabs for two ways of working.

**Clipboard tab** — the one-click flow, like the original scripts. The box shows whatever is on the clipboard. Copy text anywhere, click **Cloak Clipboard**, and the clipboard now holds the encrypted string — paste it anywhere. Copy an encrypted string and click **Uncloak Clipboard**, and the clipboard holds the original text, ready to paste (marked secret: kept out of Win+V history and cleared when you close the app).

**Manual tab** — full control, nothing touches the clipboard unless you say so. Type or **Paste** text into the input box, click **Cloak** or **Uncloak**, and the result appears below — on screen only. Click **Copy** when you actually want it on the clipboard. Reading a secret this way means it never reaches the clipboard at all.

## The Password menu

Passwords live in the **Password** menu (or press **Ctrl+P** for a new one). The menu shows the last password used and up to ten recent ones, each displayed only as its first and last character (`h...!`) to jog your memory without revealing it. Picking an entry makes it the active password — shown masked in the status bar — and it stays active for every Cloak/Uncloak until you pick another. If no password is selected, clicking Cloak or Uncloak simply opens the password dialog.

A password only enters the history after it *works* — a successful cloak or uncloak — so typos and wrong guesses are never remembered.

The history is stored encrypted with Windows DPAPI in `%APPDATA%\CloakClip\passwordHistory.bin`, tied to your Windows account: unreadable from other accounts or machines, but decryptable by any program running as you. If you don't want passwords kept at all, use **Password > Clear Password History**.

A wrong password, or text that was not encrypted, shows a message in the status bar and changes nothing.

**Clear Clipboard & History** (on the Clipboard tab) empties the clipboard and purges Windows clipboard history (Win+V), which is the way to clean up plain text that *other* apps copied — for example the password you copied out of an email in order to cloak it. Items you pinned in Win+V are kept.

## How your secrets are protected

Windows keeps a history of everything copied (Win+V) and can sync it to the cloud, so a decrypted secret sitting on the clipboard normally outlives both the paste and the app. CloakClip avoids that three ways:

- **The Manual tab keeps secrets off the clipboard entirely.** Uncloaked text is only displayed; if you just need to read a message, it never leaves the window.
- **Any uncloaked text that does reach the clipboard is marked secret** (both the Clipboard tab's Uncloak and the Manual tab's Copy) using the same Windows clipboard formats password managers use, so Windows keeps it out of clipboard history and cloud sync. It still pastes normally.
- **Re-copying a secret by hand is caught.** If you copy an uncloaked text again yourself — selecting it on screen, or re-copying it after pasting — that ordinary copy has no secret marking, so Windows records it. CloakClip watches for its session secrets reappearing on the clipboard, re-protects them, and deletes the recorded entries from Win+V history.
- **Closing the app cleans up**: a copied secret is cleared from the clipboard, and any session secret that reached Win+V history is deleted from it. Cloaked text is left alone, since it is encrypted and you may still want to paste it.

The guard can only match exact text from the current session — a secret edited after pasting, or one uncloaked in a previous run, is not recognized. For those, use **Clear Clipboard & History**.

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
