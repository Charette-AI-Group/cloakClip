"""Build the standalone CloakClip.exe (single file, no Python needed).

    .venv\\Scripts\\python.exe tools\\buildStandalone.py

The result is dist\\CloakClip.exe — copy it anywhere and double-click.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

projectRoot = Path(__file__).resolve().parents[1]
iconFile = projectRoot / "src" / "cloakClip" / "resources" / "cloakClip.ico"
resourcesDir = projectRoot / "src" / "cloakClip" / "resources"
distDir = projectRoot / "dist"
buildDir = projectRoot / "build"

# Qt ships far more than this app uses; excluding the heavy unused modules
# keeps the single file to a reasonable size.
excludedModules = (
    "PySide6.QtNetwork", "PySide6.QtQml", "PySide6.QtQuick", "PySide6.QtQuick3D",
    "PySide6.QtQuickWidgets", "PySide6.Qt3DCore", "PySide6.Qt3DRender",
    "PySide6.QtMultimedia", "PySide6.QtMultimediaWidgets", "PySide6.QtWebEngineCore",
    "PySide6.QtWebEngineWidgets", "PySide6.QtWebChannel", "PySide6.QtSql",
    "PySide6.QtTest", "PySide6.QtCharts", "PySide6.QtDataVisualization",
    "PySide6.QtOpenGL", "PySide6.QtOpenGLWidgets", "PySide6.QtPdf",
    "PySide6.QtPdfWidgets", "PySide6.QtSerialPort", "PySide6.QtBluetooth",
    "PySide6.QtPositioning", "PySide6.QtSensors", "PySide6.QtDesigner",
    "PySide6.QtHelp", "PySide6.QtUiTools", "PySide6.QtSvgWidgets",
    "tkinter", "unittest", "pytest", "pydoc", "doctest",
)


def buildCommand() -> list[str]:
    command = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm", "--clean",
        "--onefile",
        "--windowed",  # no console window behind the GUI
        "--name", "CloakClip",
        "--icon", str(iconFile),
        # The window icon is read at runtime, so the file must be bundled too.
        "--add-data", f"{resourcesDir}{os.pathsep}resources",
        # winrt loads its Windows projections dynamically; static analysis
        # alone misses them and clipboard-history support would break.
        "--collect-submodules", "winrt",
        "--collect-binaries", "winrt",
    ]
    for module in excludedModules:
        command += ["--exclude-module", module]
    command.append(str(projectRoot / "src" / "cloakClip" / "main.py"))
    return command


def main() -> int:
    if not iconFile.exists():
        print(f"Icon missing: {iconFile}\nRun: python tools/makeIcon.py", file=sys.stderr)
        return 1

    for folder in (buildDir, distDir):
        if folder.exists():
            shutil.rmtree(folder, ignore_errors=True)

    print("Building CloakClip.exe — this takes a couple of minutes ...")
    result = subprocess.run(buildCommand(), cwd=str(projectRoot))
    if result.returncode != 0:
        print("PyInstaller failed.", file=sys.stderr)
        return result.returncode

    exePath = distDir / "CloakClip.exe"
    if not exePath.exists():
        print(f"Build reported success but {exePath} is missing.", file=sys.stderr)
        return 1

    megabytes = exePath.stat().st_size / (1024 * 1024)
    print(f"\nBuilt {exePath} ({megabytes:.1f} MB)")
    print("Copy it anywhere and double-click — no Python or venv needed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
