"""Application configuration — paths, defaults, and metadata."""

from __future__ import annotations

import os
import sys
from pathlib import Path

appName = "CloakClip"
appVersion = "1.0.1"
organizationName = "Charette-AI-Group"

# Help > About contents
editorName = "Francois Charette, PhD"
aiAgentName = "Claude - Fable 5"
copyrightHolder = "Charette AI Group, LLC"

def _appDataBase() -> Path:
    """Where this OS keeps per-user application data."""
    if sys.platform == "win32":
        return Path(os.environ.get("APPDATA", str(Path.home())))
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support"
    return Path(os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config")))


projectRoot = Path(__file__).resolve().parents[2]

# In a PyInstaller build the package lives in an archive, not on disk, so
# bundled files are read from the extraction directory instead.
if getattr(sys, "frozen", False):
    resourcesDir = Path(getattr(sys, "_MEIPASS", projectRoot)) / "resources"
else:
    resourcesDir = Path(__file__).resolve().parent / "resources"

# macOS has no use for .ico; both files are produced by tools/makeIcon.py.
iconFile = resourcesDir / ("cloakClip.png" if sys.platform == "darwin" else "cloakClip.ico")
appDataDir = _appDataBase() / appName
passwordHistoryFile = appDataDir / "passwordHistory.bin"
settingsFile = appDataDir / "settings.ini"
maxPasswordHistory = 10
windowTitle = appName
# The same PayPal button the website and the other apps use.
donateUrl = "https://www.paypal.com/donate/?hosted_button_id=FEM4WLD7LHY36"
# Matching the donate button in the SAE Calculator, for a consistent look
# across the apps. Dark text on yellow reads well in either theme.
donateColor = "#f0b232"
donateTextColor = "#1f1e1b"
donatePressedColor = "#d9991f"
# Indigo from the app icon; legible on both light and dark Windows themes.
accentColor = "#6366F1"
defaultWindowWidth = 620
defaultWindowHeight = 620
