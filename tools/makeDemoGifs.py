"""Record the README demo GIFs by driving the real app.

    .venv\\Scripts\\python.exe tools\\makeDemoGifs.py

Writes docs/clipboardTab.gif and docs/manualTab.gif. Frames are grabbed
from a live MainWindow, so the GIFs cannot drift from the real UI.

Runs against temporary settings and a stubbed history purge, so recording
never touches the real password history, window position or Win+V.
"""

from __future__ import annotations

import sys
import tempfile
import time
from pathlib import Path

from PIL import Image
from PySide6.QtWidgets import QApplication, QPushButton

from cloakClip import appConfig

tempDir = Path(tempfile.mkdtemp(prefix="cloakClipDemo"))
appConfig.passwordHistoryFile = tempDir / "passwordHistory.bin"
appConfig.settingsFile = tempDir / "settings.ini"

from cloakClip.services import clipboardService, themeService  # noqa: E402
from cloakClip.services.cryptoService import encryptText  # noqa: E402
from cloakClip.ui.mainWindow import MainWindow  # noqa: E402

projectRoot = Path(__file__).resolve().parents[1]
docsDir = projectRoot / "docs"

demoPassword = "correct-horse-battery"
demoSecret = "Wi-Fi guest password: swordfish"
demoNote = "Meet me at noon"

# Frame timings in milliseconds — long enough to read, short enough to loop.
holdShort = 700
holdLong = 1600


class Recorder:
    def __init__(self, app: QApplication, window: MainWindow) -> None:
        self.app = app
        self.window = window
        self.frames: list[Image.Image] = []
        self.durations: list[int] = []
        self.frameDir = Path(tempfile.mkdtemp(prefix="cloakClipFrames"))
        self.index = 0

    def pump(self, milliseconds: int) -> None:
        """Let Qt run for real time, so debounce timers actually fire."""
        deadline = time.time() + milliseconds / 1000
        while time.time() < deadline:
            self.app.processEvents()
            time.sleep(0.02)

    def capture(self, hold: int = holdShort) -> None:
        path = self.frameDir / f"frame{self.index:03d}.png"
        self.index += 1
        self.app.processEvents()
        self.window.grab().save(str(path), "PNG")
        self.frames.append(Image.open(path).convert("RGB"))
        self.durations.append(hold)

    def clickShot(self, button: QPushButton, hold: int = holdLong) -> None:
        """Show the button pressed, then the result — reads as a real click."""
        button.setDown(True)
        self.capture(250)
        button.setDown(False)
        button.click()
        self.pump(500)
        self.capture(hold)

    def save(self, outputFile: Path) -> None:
        outputFile.parent.mkdir(parents=True, exist_ok=True)
        # Flat UI colours quantise well, so a small palette keeps the file
        # small without visible banding.
        palette = [frame.quantize(colors=96, method=Image.Quantize.MEDIANCUT)
                   for frame in self.frames]
        palette[0].save(
            outputFile,
            save_all=True,
            append_images=palette[1:],
            duration=self.durations,
            loop=0,
            optimize=True,
            disposal=2,
        )
        sizeKb = outputFile.stat().st_size / 1024
        print(f"Wrote {outputFile.relative_to(projectRoot)} "
              f"({len(palette)} frames, {sizeKb:.0f} KB)")


def recordClipboardTab(app: QApplication, window: MainWindow) -> None:
    recorder = Recorder(app, window)
    tab = window.clipboardTab
    window.tabWidget.setCurrentWidget(tab)
    # Only as tall as the content needs: empty space wastes GIF bytes and
    # makes the text smaller once GitHub scales it to the column width.
    window.resize(620, 330)

    clipboardService.writeText(demoSecret)
    window.usePassword(demoPassword)
    window.statusMessage("Copy any text — it appears here.")
    recorder.pump(300)
    recorder.capture(holdLong)

    recorder.clickShot(tab.cloakButton)
    recorder.clickShot(tab.uncloakButton)

    # Editing the uncloaked text in place, then sending it back cloaked.
    for edited in ("Wi-Fi guest password: swordfish — ",
                   "Wi-Fi guest password: swordfish — changes Friday"):
        tab.previewEdit.setPlainText(edited)
        recorder.pump(420)
        recorder.capture(holdShort)
    recorder.capture(holdLong)
    recorder.clickShot(tab.cloakButton)

    recorder.save(docsDir / "clipboardTab.gif")


def recordManualTab(app: QApplication, window: MainWindow) -> None:
    recorder = Recorder(app, window)
    tab = window.manualTab
    window.tabWidget.setCurrentWidget(tab)
    window.resize(620, 420)
    tab.clearFields()
    window.usePassword(demoPassword)
    window.statusMessage("Type on the left — the encrypted text follows.")
    recorder.capture(holdLong)

    # Type in bursts so the debounce fires mid-way: that is the live sync.
    typed = ""
    for chunk in ("Meet ", "me at ", "noon"):
        typed += chunk
        tab.plainEdit.setPlainText(typed)
        recorder.pump(420)
        recorder.capture(holdShort)
    recorder.capture(holdLong)

    # Now the other direction: paste a cloaked string, read the plain text.
    tab.clearFields()
    recorder.capture(holdShort)
    tab.cloakEdit.setPlainText(encryptText(demoNote, demoPassword))
    recorder.pump(500)
    recorder.capture(holdLong)

    recorder.save(docsDir / "manualTab.gif")


def main() -> int:
    app = QApplication(sys.argv)
    # Light theme reads better embedded in documentation.
    themeService.applyTheme(themeService.lightTheme)
    # Never touch the real Win+V history while recording.
    clipboardService.deleteHistoryTexts = lambda texts: 0

    window = MainWindow()
    window.show()
    app.processEvents()

    recordClipboardTab(app, window)
    recordManualTab(app, window)

    clipboardService.clearText()
    window.close()
    print("Clipboard cleared; recording used temporary settings only.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
