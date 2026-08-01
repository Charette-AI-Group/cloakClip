# CloakClip

Encrypt and decrypt clipboard text with a password

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
