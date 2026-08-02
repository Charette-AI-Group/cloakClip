"""Application entry point — wiring only."""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from cloakClip import appConfig
from cloakClip.services import themeService
from cloakClip.ui.mainWindow import MainWindow


def runSelfTest(reportPath: str | None) -> int:
    """Check that a build has everything it needs, and report it.

    Worth having because the pieces that a packaged build tends to lose —
    the bundled icon, the winrt clipboard bindings — fail quietly at
    runtime rather than crashing, so a build can look fine and silently
    have no clipboard-history support.
    """
    from cloakClip.services import clipboardService

    iconFound = appConfig.iconFile.exists()
    winrtFound = clipboardService.winrtClipboard is not None
    report = "\n".join(
        [
            f"frozen={getattr(sys, 'frozen', False)}",
            f"version={appConfig.appVersion}",
            f"iconFile={appConfig.iconFile}",
            f"iconFound={iconFound}",
            f"winrtFound={winrtFound}",
            f"historyEnabled={clipboardService.isHistoryEnabled()}",
        ]
    )
    if reportPath:
        Path(reportPath).write_text(report, encoding="utf-8")
    else:
        print(report)
    return 0 if iconFound and winrtFound else 1


def main() -> int:
    if "--selftest" in sys.argv:
        index = sys.argv.index("--selftest")
        reportPath = sys.argv[index + 1] if len(sys.argv) > index + 1 else None
        return runSelfTest(reportPath)

    app = QApplication(sys.argv)
    app.setApplicationName(appConfig.appName)
    app.setApplicationVersion(appConfig.appVersion)
    app.setOrganizationName(appConfig.organizationName)
    if appConfig.iconFile.exists():
        app.setWindowIcon(QIcon(str(appConfig.iconFile)))
    # Follows Windows unless the user picked an override under Help > Theme.
    themeService.applyTheme(themeService.loadTheme())

    mainWindow = MainWindow()
    mainWindow.show()

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
