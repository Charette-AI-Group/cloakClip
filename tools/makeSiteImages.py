"""Generate the still images used by the docs/ website.

    .venv\\Scripts\\python.exe tools\\makeSiteImages.py

Writes docs/img/. Like the demo GIFs, these are grabbed from a live
MainWindow so they cannot drift from the real UI. Runs against temporary
settings and a stubbed history purge, so it never touches real state.
"""

from __future__ import annotations

import shutil
import sys
import tempfile
import time
from pathlib import Path

from PySide6.QtWidgets import QApplication

from cloakClip import appConfig

tempDir = Path(tempfile.mkdtemp(prefix="cloakClipSite"))
appConfig.passwordHistoryFile = tempDir / "passwordHistory.bin"
appConfig.settingsFile = tempDir / "settings.ini"

from cloakClip.services import (  # noqa: E402
    clipboardService,
    passwordHistoryService,
    themeService,
)
from cloakClip.services.cryptoService import encryptText  # noqa: E402
from cloakClip.ui.dialogs.passwordDialog import PasswordDialog  # noqa: E402
from cloakClip.ui.mainWindow import MainWindow  # noqa: E402

projectRoot = Path(__file__).resolve().parents[1]
imageDir = projectRoot / "docs" / "img"

demoPassword = "correct-horse-battery"
demoSecret = "Wi-Fi guest password: swordfish"


def pump(app: QApplication, seconds: float) -> None:
    deadline = time.time() + seconds
    while time.time() < deadline:
        app.processEvents()
        time.sleep(0.02)


def saveWidget(widget, name: str) -> None:
    widget.grab().save(str(imageDir / name), "PNG")
    print(f"wrote docs/img/{name}")


def main() -> int:
    imageDir.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(appConfig.resourcesDir / "cloakClip.png", imageDir / "icon.png")
    print("wrote docs/img/icon.png")

    clipboardService.deleteHistoryTexts = lambda texts: 0
    app = QApplication(sys.argv)
    # Light throughout: the site is light, and mixed shots look accidental.
    themeService.applyTheme(themeService.lightTheme)

    window = MainWindow()
    window.askCloseAction = lambda: "close"
    window.resize(620, 360)
    window.show()
    pump(app, 0.4)

    # The Clipboard tab holding an uncloaked message.
    window.usePassword(demoPassword)
    clipboardService.writeText(encryptText(demoSecret, demoPassword))
    pump(app, 0.4)
    window.clipboardTab.uncloakButton.click()
    pump(app, 0.5)
    saveWidget(window, "clipboardTab.png")

    # The Manual tab with both fields populated.
    window.tabWidget.setCurrentWidget(window.manualTab)
    window.resize(620, 430)
    window.manualTab.plainEdit.setPlainText("Meet me at noon on Tuesday")
    pump(app, 0.7)
    saveWidget(window, "manualTab.png")

    # The password dialog, with a history so the shortcut button is present.
    passwordHistoryService.rememberPassword("hunter2!")
    dialog = PasswordDialog(window)
    dialog.show()
    pump(app, 0.3)
    dialog.adjustSize()
    pump(app, 0.2)
    saveWidget(dialog, "passwordDialog.png")
    dialog.close()

    # The close dialog, showing both exit choices and Cancel.
    closeBox = window.buildCloseDialog()
    closeBox.show()
    pump(app, 0.3)
    closeBox.adjustSize()
    pump(app, 0.2)
    saveWidget(closeBox, "closeDialog.png")
    closeBox.close()

    clipboardService.clearText()
    window.close()
    print("Clipboard cleared; temporary settings only.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
