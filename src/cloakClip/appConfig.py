"""Application configuration — paths, defaults, and metadata."""

from __future__ import annotations

import os
import sys
from pathlib import Path

appName = "CloakClip"
appVersion = "0.8.0"
organizationName = "Charette-AI-Group"

# Help > About contents
editorName = "Francois Charette, PhD"
aiAgentName = "Claude - Fable 5"
copyrightHolder = "Charette AI Group, LLC"

projectRoot = Path(__file__).resolve().parents[2]

# In a PyInstaller build the package lives in an archive, not on disk, so
# bundled files are read from the extraction directory instead.
if getattr(sys, "frozen", False):
    resourcesDir = Path(getattr(sys, "_MEIPASS", projectRoot)) / "resources"
else:
    resourcesDir = Path(__file__).resolve().parent / "resources"

iconFile = resourcesDir / "cloakClip.ico"
appDataDir = Path(os.environ.get("APPDATA", str(Path.home()))) / appName
passwordHistoryFile = appDataDir / "passwordHistory.bin"
settingsFile = appDataDir / "settings.ini"
maxPasswordHistory = 10
windowTitle = appName
# Indigo from the app icon; legible on both light and dark Windows themes.
accentColor = "#6366F1"
defaultWindowWidth = 620
defaultWindowHeight = 620
