"""Main application window — tabs, menus, and shared password state."""

from __future__ import annotations

import datetime
import threading
from functools import partial

from PySide6.QtCore import QTimer
from PySide6.QtGui import QAction, QCloseEvent, QGuiApplication, QKeySequence
from PySide6.QtWidgets import QLabel, QMainWindow, QMessageBox

from cloakClip import appConfig
from cloakClip.services import clipboardService, passwordHistoryService, windowStateService
from cloakClip.ui.clipboardTab import ClipboardTab
from cloakClip.ui.dialogs.passwordDialog import PasswordDialog
from cloakClip.ui.manualTab import ManualTab
from cloakClip.ui.widgets.fullWidthTabWidget import FullWidthTabWidget


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
        # Every plain text uncloaked this session, so re-copies of it can be
        # re-protected and swept out of Win+V history.
        self.sessionSecrets: set[str] = set()

        self.buildMenuBar()

        self.tabWidget = FullWidthTabWidget()
        self.clipboardTab = ClipboardTab(self)
        self.manualTab = ManualTab(self)
        self.tabWidget.addTab(self.clipboardTab, "&Clipboard")
        self.tabWidget.addTab(self.manualTab, "&Manual")
        self.setCentralWidget(self.tabWidget)

        self.passwordLabel = QLabel("No password selected")
        self.statusBar().addPermanentWidget(self.passwordLabel)
        self.statusBar().showMessage("Ready")

        self.restoreWindowGeometry()
        QGuiApplication.clipboard().dataChanged.connect(self.guardSecretReappearance)

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
        self.manualTab.onPasswordActivated()

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

    # -------------------------------------------------------- window state

    def restoreWindowGeometry(self) -> None:
        geometry = windowStateService.loadGeometry()
        if geometry is not None and self.restoreGeometry(geometry):
            self.moveOnScreenIfStranded()

    def moveOnScreenIfStranded(self) -> None:
        # A saved position can point at a monitor that is no longer attached,
        # which would restore the window somewhere the user cannot reach.
        frame = self.frameGeometry()
        if any(
            screen.availableGeometry().intersects(frame)
            for screen in QGuiApplication.screens()
        ):
            return
        self.resize(appConfig.defaultWindowWidth, appConfig.defaultWindowHeight)
        primary = QGuiApplication.primaryScreen()
        if primary is not None:
            self.move(primary.availableGeometry().center() - self.rect().center())

    # ----------------------------------------------------- shared clipboard

    def statusMessage(self, message: str) -> None:
        self.statusBar().showMessage(message)

    def registerSecret(self, text: str) -> None:
        self.sessionSecrets.add(text)

    def guardSecretReappearance(self) -> None:
        # A secret uncloaked this session can come back as an ordinary copy —
        # the user selecting the shown text, or re-copying it after pasting.
        # Such a copy is unmarked, so Win+V records it. Re-write it marked and
        # sweep the recorded copy back out of history.
        text = clipboardService.readText()
        if not text or text not in self.sessionSecrets:
            return
        if clipboardService.currentTextIsMarkedSecret():
            return
        if self.writeClipboard(text, secret=True):
            self.statusMessage("Secret re-copied — protected it again.")
        # The history service records the unmarked copy asynchronously; give
        # it a moment to appear before sweeping it out.
        QTimer.singleShot(800, self.purgeSecretsFromHistory)

    def purgeSecretsFromHistory(self) -> None:
        secrets = self.sessionSecrets.copy()
        if not secrets:
            return
        # Blocking WinRT calls; keep them off the GUI thread.
        threading.Thread(
            target=clipboardService.deleteHistoryTexts, args=(secrets,), daemon=True
        ).start()

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
        self.manualTab.clearFields()

        if not clipboardCleared:
            self.statusMessage("The clipboard is busy — please try again.")
        elif historyCleared:
            self.statusMessage("Clipboard and clipboard history cleared.")
        else:
            self.statusMessage("Clipboard cleared; clipboard history was unavailable.")

    def closeEvent(self, event: QCloseEvent) -> None:
        windowStateService.saveGeometry(self.saveGeometry())
        # Never leave an uncloaked secret behind. Cloaked text is harmless and
        # is left alone so it can still be pasted after the window closes.
        if self.lastWriteWasSecret and clipboardService.readText() == self.lastClipboardWrite:
            clipboardService.clearText()
        # Final sweep: any session secret that reached Win+V history (e.g. a
        # manual re-copy the timer had not caught yet) is deleted. Deliberately
        # synchronous — the process may exit right after this.
        if self.sessionSecrets:
            clipboardService.deleteHistoryTexts(self.sessionSecrets.copy())
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
