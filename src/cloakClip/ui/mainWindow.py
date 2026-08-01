"""Main application window — tabs, menus, and shared password state."""

from __future__ import annotations

import datetime
from functools import partial

from PySide6.QtGui import QAction, QCloseEvent, QKeySequence
from PySide6.QtWidgets import QLabel, QMainWindow, QMessageBox, QTabWidget

from cloakClip import appConfig
from cloakClip.services import clipboardService, passwordHistoryService
from cloakClip.ui.clipboardTab import ClipboardTab
from cloakClip.ui.dialogs.passwordDialog import PasswordDialog
from cloakClip.ui.manualTab import ManualTab


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(appConfig.windowTitle)
        self.resize(appConfig.defaultWindowWidth, appConfig.defaultWindowHeight)

        # Remember what CloakClip itself put on the clipboard, so it can tell
        # its own writes from the user's copies and clean up secrets on exit.
        self.lastClipboardWrite: str | None = None
        self.lastWriteWasSecret = False
        self.activePassword: str | None = None

        self.buildMenuBar()

        self.tabWidget = QTabWidget()
        self.clipboardTab = ClipboardTab(self)
        self.manualTab = ManualTab(self)
        self.tabWidget.addTab(self.clipboardTab, "&Clipboard")
        self.tabWidget.addTab(self.manualTab, "&Manual")
        self.setCentralWidget(self.tabWidget)

        self.passwordLabel = QLabel("No password selected")
        self.statusBar().addPermanentWidget(self.passwordLabel)
        self.statusBar().showMessage("Ready")

    def buildMenuBar(self) -> None:
        # Menus are kept as attributes: features can extend them later, and it
        # prevents the Python wrappers from being garbage-collected.
        fileMenu = self.fileMenu = self.menuBar().addMenu("&File")

        self.exitAction = QAction("E&xit", self)
        self.exitAction.setShortcut(QKeySequence("Ctrl+Q"))
        self.exitAction.triggered.connect(self.close)
        fileMenu.addAction(self.exitAction)

        self.passwordMenu = self.menuBar().addMenu("&Password")
        self.passwordMenu.aboutToShow.connect(self.rebuildPasswordMenu)
        self.rebuildPasswordMenu()

        helpMenu = self.helpMenu = self.menuBar().addMenu("&Help")

        self.aboutAction = QAction("&About", self)
        self.aboutAction.triggered.connect(self.onHelpAbout)
        helpMenu.addAction(self.aboutAction)

    def rebuildPasswordMenu(self) -> None:
        menu = self.passwordMenu
        menu.clear()
        passwords = passwordHistoryService.loadPasswords()

        if passwords:
            lastMask = passwordHistoryService.maskPassword(passwords[0])
            lastAction = menu.addAction(f"Last Password Used ({lastMask})")
            lastAction.triggered.connect(partial(self.usePassword, passwords[0]))
            menu.addSeparator()
            for password in passwords:
                mask = passwordHistoryService.maskPassword(password)
                action = menu.addAction(mask)
                action.triggered.connect(partial(self.usePassword, password))
        else:
            noneAction = menu.addAction("No Passwords Remembered Yet")
            noneAction.setEnabled(False)

        menu.addSeparator()
        newAction = menu.addAction("&New Password...")
        newAction.setShortcut(QKeySequence("Ctrl+P"))
        newAction.triggered.connect(self.onNewPassword)
        clearAction = menu.addAction("Clear Password History")
        clearAction.setEnabled(bool(passwords))
        clearAction.triggered.connect(self.onClearPasswordHistory)

    # ------------------------------------------------------------ passwords

    def usePassword(self, password: str) -> None:
        self.activePassword = password
        mask = passwordHistoryService.maskPassword(password)
        self.passwordLabel.setText(f"Password: {mask}")
        self.statusMessage(f"Password {mask} selected.")

    def onNewPassword(self) -> None:
        password = PasswordDialog.getPassword(self)
        if password:
            self.usePassword(password)

    def onClearPasswordHistory(self) -> None:
        passwordHistoryService.clearPasswords()
        self.activePassword = None
        self.passwordLabel.setText("No password selected")
        self.statusMessage("Password history cleared.")

    def ensurePassword(self) -> str | None:
        if self.activePassword:
            return self.activePassword
        self.onNewPassword()
        if self.activePassword is None:
            self.statusMessage("Enter a password first (Password menu, Ctrl+P).")
        return self.activePassword

    def rememberActivePassword(self) -> None:
        if self.activePassword:
            passwordHistoryService.rememberPassword(self.activePassword)

    # ----------------------------------------------------- shared clipboard

    def statusMessage(self, message: str) -> None:
        self.statusBar().showMessage(message)

    def writeClipboard(self, text: str, secret: bool) -> bool:
        if not clipboardService.writeText(text, secret=secret):
            self.statusMessage("The clipboard is busy — please try again.")
            return False
        self.lastClipboardWrite = text
        self.lastWriteWasSecret = secret
        return True

    def clearClipboardAndHistory(self) -> None:
        clipboardCleared = clipboardService.clearText()
        historyCleared = clipboardService.clearHistory()
        self.lastClipboardWrite = None
        self.lastWriteWasSecret = False
        self.manualTab.outputEdit.clear()

        if not clipboardCleared:
            self.statusMessage("The clipboard is busy — please try again.")
        elif historyCleared:
            self.statusMessage("Clipboard and clipboard history cleared.")
        else:
            self.statusMessage("Clipboard cleared; clipboard history was unavailable.")

    def closeEvent(self, event: QCloseEvent) -> None:
        # Never leave an uncloaked secret behind. Cloaked text is harmless and
        # is left alone so it can still be pasted after the window closes.
        if self.lastWriteWasSecret and clipboardService.readText() == self.lastClipboardWrite:
            clipboardService.clearText()
        super().closeEvent(event)

    # ---------------------------------------------------------------- about

    def buildAboutText(self) -> str:
        year = datetime.date.today().year
        return (
            f"<h3>{appConfig.appName}</h3>"
            f"<p>Version {appConfig.appVersion}</p>"
            f"<p>Editor: {appConfig.editorName}<br>"
            f"AI Agent: {appConfig.aiAgentName}</p>"
            f"<p>&copy; {year} {appConfig.copyrightHolder}</p>"
        )

    def onHelpAbout(self) -> None:
        aboutBox = QMessageBox(self)
        aboutBox.setWindowTitle(f"About {appConfig.appName}")
        aboutBox.setText(self.buildAboutText())
        # QMessageBox ignores resize/setMinimumWidth; widening its label works.
        aboutBox.setStyleSheet("QLabel { min-width: 420px; }")
        aboutBox.exec()
