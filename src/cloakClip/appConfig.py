"""Application configuration — paths, defaults, and metadata."""

from __future__ import annotations

import os
from pathlib import Path

appName = "CloakClip"
appVersion = "0.1.0"
organizationName = "Charette-AI-Group"

# Help > About contents
editorName = "Francois Charette, PhD"
aiAgentName = "Claude - Fable 5"
copyrightHolder = "Charette AI Group, LLC"

projectRoot = Path(__file__).resolve().parents[2]
resourcesDir = Path(__file__).resolve().parent / "resources"
appDataDir = Path(os.environ.get("APPDATA", str(Path.home()))) / appName
passwordHistoryFile = appDataDir / "passwordHistory.bin"
maxPasswordHistory = 10
windowTitle = appName
defaultWindowWidth = 620
defaultWindowHeight = 620
