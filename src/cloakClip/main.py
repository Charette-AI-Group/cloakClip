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
    from cloakClip.services import clipboardService, passwordHistoryService

    iconFound = appConfig.iconFile.exists()
    backend = clipboardService.backend
    # On Windows the protections are the point, so their absence is a failed
    # build. Elsewhere there is no backend yet and that is expected.
    expectProtections = sys.platform == "win32"
    protectionsFound = backend.supportsHistory and backend.supportsSecretMarking
    report = "\n".join(
        [
            f"platform={sys.platform}",
            f"frozen={getattr(sys, 'frozen', False)}",
            f"version={appConfig.appVersion}",
            f"iconFile={appConfig.iconFile}",
            f"iconFound={iconFound}",
            f"clipboardBackend={backend.name}",
            f"secretMarking={backend.supportsSecretMarking}",
            f"historySupport={backend.supportsHistory}",
            f"historyEnabled={clipboardService.isHistoryEnabled()}",
            f"passwordStore={passwordHistoryService.dpapiAvailable}",
        ]
    )
    if reportPath:
        Path(reportPath).write_text(report, encoding="utf-8")
    else:
        print(report)
    if not iconFound:
        return 1
    return 0 if protectionsFound or not expectProtections else 1


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
