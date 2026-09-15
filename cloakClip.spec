# PyInstaller build configuration — windowed app, one file or one folder.
#
#     python -m PyInstaller cloakClip.spec --noconfirm
#         -> dist/CloakClip.exe (Windows), dist/CloakClip.app (macOS)
#
# With CLOAKCLIP_ONEDIR=1 in the environment it builds a folder bundle:
#
#         -> dist/CloakClip/CloakClip.exe
#
# That is what the Windows installer packages (tools/buildInstaller.py). A
# one-file build unpacks itself to a temp folder on every launch, which is a
# fair price for a download you hand somebody, and the wrong one for an
# application they installed.

import os
import sys

from PyInstaller.utils.hooks import collect_dynamic_libs, collect_submodules

# Pillow (build extra) converts the icon to the platform format at build time.
appIcon = (
    "src/cloakClip/resources/cloakClip.png"
    if sys.platform == "darwin"
    else "src/cloakClip/resources/cloakClip.ico"
)

oneDir = os.environ.get("CLOAKCLIP_ONEDIR") == "1"

# winrt loads its Windows projections dynamically, so static analysis alone
# misses them and the clipboard-history protections would silently vanish.
hiddenImports = collect_submodules("winrt") if sys.platform == "win32" else []
extraBinaries = collect_dynamic_libs("winrt") if sys.platform == "win32" else []

# Qt ships far more than this app uses.
excludedModules = [
    "PySide6.QtNetwork", "PySide6.QtQml", "PySide6.QtQuick", "PySide6.QtQuick3D",
    "PySide6.QtQuickWidgets", "PySide6.Qt3DCore", "PySide6.Qt3DRender",
    "PySide6.QtMultimedia", "PySide6.QtMultimediaWidgets", "PySide6.QtWebEngineCore",
    "PySide6.QtWebEngineWidgets", "PySide6.QtWebChannel", "PySide6.QtSql",
    "PySide6.QtCharts", "PySide6.QtDataVisualization", "PySide6.QtOpenGL",
    "PySide6.QtOpenGLWidgets", "PySide6.QtPdf", "PySide6.QtPdfWidgets",
    "PySide6.QtSerialPort", "PySide6.QtBluetooth", "PySide6.QtPositioning",
    "PySide6.QtSensors", "PySide6.QtDesigner", "PySide6.QtHelp",
    "PySide6.QtUiTools", "PySide6.QtSvgWidgets",
    "tkinter", "unittest", "pydoc", "doctest",
]

a = Analysis(
    ["src/cloakClip/main.py"],
    pathex=["src"],
    binaries=extraBinaries,
    datas=[("src/cloakClip/resources", "resources")],
    hiddenimports=hiddenImports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludedModules,
    noarchive=False,
)

pyz = PYZ(a.pure)

exeArguments = {
    "name": "CloakClip",
    "debug": False,
    "bootloader_ignore_signals": False,
    "strip": False,
    "upx": False,
    "upx_exclude": [],
    "console": False,
    "icon": appIcon,
    "disable_windowed_traceback": False,
    "argv_emulation": False,
    "target_arch": None,
    "codesign_identity": None,
    "entitlements_file": None,
}

if oneDir:
    exe = EXE(pyz, a.scripts, [], exclude_binaries=True, **exeArguments)
    bundleTarget = COLLECT(
        exe,
        a.binaries,
        a.datas,
        strip=False,
        upx=False,
        upx_exclude=[],
        name="CloakClip",
    )
else:
    exe = EXE(pyz, a.scripts, a.binaries, a.datas, [], runtime_tmpdir=None, **exeArguments)
    bundleTarget = exe

if sys.platform == "darwin":
    app = BUNDLE(
        bundleTarget,
        name="CloakClip.app",
        icon=appIcon,
        bundle_identifier="com.charette-ai-group.cloakClip",
        info_plist={
            "NSHighResolutionCapable": True,
        },
    )
