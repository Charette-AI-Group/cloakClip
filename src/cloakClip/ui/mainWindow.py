"""Main application window — tabs, menus, and shared password state."""

from __future__ import annotations

import datetime
import threading
from functools import partial

from PySide6.QtCore import QEvent, QTimer
from PySide6.QtGui import (
    QAction,
    QActionGroup,
    QCloseEvent,
    QColor,
    QGuiApplication,
    QKeySequence,
    QPalette,
)
from PySide6.QtWidgets import QLabel, QMainWindow, QMessageBox

from cloakClip import appConfig
from cloakClip.services import (
    clipboardService,
    passwordHistoryService,
    themeService,
    windowStateService,
)
from cloakClip.ui.clipboardTab import ClipboardTab
from cloakClip.ui.dialogs.passwordDialog import PasswordDialog
from cloakClip.ui.manualTab import ManualTab
from cloakClip.ui.widgets.fullWidthTabWidget import FullWidthTabWidget


def rgba(color: QColor, alphaFactor: float | None = None) -> str:
    """Qt stylesheet rgba() string, optionally re-scaling the alpha."""
    alpha = color.alphaF() if alphaFactor is None else alphaFactor
    return f"rgba({color.red()}, {color.green()}, {color.blue()}, {alpha:.3f})"


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
        self._applyingTabStyle = False
        # Set when the user has already chosen how to exit, so the close
        # dialog is not shown on top of their choice.
        self._closeWithoutPrompt = False
        # Every plain text uncloaked this session, so re-copies of it can be
        # re-protected and swept out of Win+V history.
        self.sessionSecrets: set[str] = set()

        self.buildMenuBar()

        self.tabWidget = FullWidthTabWidget()
        self.clipboardTab = ClipboardTab(self)
        self.manualTab = ManualTab(self)
        self.tabWidget.addTab(self.clipboardTab, "&Clipboard")
        self.tabWidget.addTab(self.manualTab, "&Manual")
        self.applyTabEmphasis()
        self.setCentralWidget(self.tabWidget)

        self.passwordLabel = QLabel("No password selected")
        self.statusBar().addPermanentWidget(self.passwordLabel)
        self.statusBar().showMessage("Ready")

        self.restoreWindowGeometry()
        QGuiApplication.clipboard().dataChanged.connect(self.guardSecretReappearance)

    def changeEvent(self, event) -> None:
        super().changeEvent(event)
        # The tab styling is built from palette colours, so it must be rebuilt
        # whenever the palette changes — a theme override here, or Windows
        # switching light/dark while the app is running.
        paletteChanged = event.type() in (
            QEvent.Type.PaletteChange,
            QEvent.Type.ApplicationPaletteChange,
        )
        if paletteChanged and not self._applyingTabStyle:
            self.applyTabEmphasis()

    def applyTabEmphasis(self) -> None:
        """Make the tabs read as buttons rather than plain labels.

        Colours come from the palette (plus the app's accent) so the styling
        holds up in both the light and dark Windows themes.
        """
        self._applyingTabStyle = True
        try:
            self.buildTabStyle()
        finally:
            self._applyingTabStyle = False

    def buildTabStyle(self) -> None:
        tabBar = self.tabWidget.tabBar()
        # Base the size on the window font, not the tab bar's current one:
        # this runs again on a theme change and must not compound.
        font = self.font()
        font.setBold(True)
        font.setPointSizeF(font.pointSizeF() * 1.15)
        tabBar.setFont(font)

        accent = QColor(appConfig.accentColor)
        idle = QColor(self.palette().color(QPalette.ColorRole.WindowText))
        idle.setAlpha(145)
        divider = QColor(idle)
        divider.setAlpha(60)

        self.tabWidget.setStyleSheet(f"""
            QTabWidget::pane {{
                border: none;
                border-top: 1px solid {rgba(divider)};
            }}
            QTabBar::tab {{
                padding: 10px 8px;
                border: none;
                border-bottom: 3px solid transparent;
                color: {rgba(idle)};
            }}
            QTabBar::tab:hover {{
                color: {rgba(accent)};
                background-color: {rgba(accent, 0.12)};
            }}
            QTabBar::tab:selected {{
                color: {rgba(accent)};
                border-bottom: 3px solid {rgba(accent)};
                background-color: {rgba(accent, 0.08)};
            }}
        """)

    def buildMenuBar(self) -> None:
        # Menus are kept as attributes: features can extend them later, and it
        # prevents the Python wrappers from being garbage-collected.
        fileMenu = self.fileMenu = self.menuBar().addMenu("&File")

        self.exitAction = QAction("E&xit", self)
        self.exitAction.setShortcut(QKeySequence("Ctrl+Q"))
        self.exitAction.triggered.connect(self.close)
        fileMenu.addAction(self.exitAction)

        self.exitAndClearAction = QAction("Exit and Clear &All!", self)
        self.exitAndClearAction.setShortcut(QKeySequence("Ctrl+Shift+Q"))
        self.exitAndClearAction.triggered.connect(self.onExitAndClearAll)
        fileMenu.addAction(self.exitAndClearAction)

        self.passwordMenu = self.menuBar().addMenu("&Password")
        self.passwordMenu.aboutToShow.connect(self.rebuildPasswordMenu)
        self.rebuildPasswordMenu()

        helpMenu = self.helpMenu = self.menuBar().addMenu("&Help")

        self.themeMenu = helpMenu.addMenu("&Theme")
        self.themeGroup = QActionGroup(self)
        self.themeGroup.setExclusive(True)
        self.themeActions: dict[str, QAction] = {}
        activeTheme = themeService.loadTheme()
        for theme in themeService.themeChoices:
            action = QAction(themeService.themeLabels[theme], self)
            action.setCheckable(True)
            action.setChecked(theme == activeTheme)
            action.triggered.connect(partial(self.onThemeChosen, theme))
            self.themeGroup.addAction(action)
            self.themeMenu.addAction(action)
            self.themeActions[theme] = action

        helpMenu.addSeparator()

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

    def onThemeChosen(self, theme: str) -> None:
        themeService.saveTheme(theme)
        # The tab styling is rebuilt by changeEvent once the new palette
        # actually arrives — doing it here would use the old colours.
        themeService.applyTheme(theme)
        if theme == themeService.systemTheme:
            self.statusMessage("Theme follows the Windows setting.")
        else:
            self.statusMessage(f"{theme.capitalize()} theme applied to CloakClip.")

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
        self.clipboardTab.clearPreview()

        if not clipboardCleared:
            self.statusMessage("The clipboard is busy — please try again.")
        elif historyCleared:
            self.statusMessage("Clipboard and clipboard history cleared.")
        else:
            self.statusMessage("Clipboard cleared; clipboard history was unavailable.")

    def buildCloseDialog(self) -> QMessageBox:
        """The dialog shown when closing without having said what to do."""
        box = QMessageBox(self)
        box.setWindowTitle(f"Close {appConfig.appName}")
        box.setIcon(QMessageBox.Icon.Question)
        box.setText(f"Close {appConfig.appName}?")
        box.setInformativeText(
            "<b>OK</b> clears an uncloaked secret from the clipboard and removes "
            "this session's secrets from Windows clipboard history."
            "<br><br><b>OK - Clear All!</b> also empties the clipboard entirely and "
            "purges the whole clipboard history, so nothing is left behind whether "
            "CloakClip was tracking it or not."
        )
        self.closeOkButton = box.addButton("OK", QMessageBox.ButtonRole.AcceptRole)
        self.closeClearButton = box.addButton(
            "OK - Clear All!", QMessageBox.ButtonRole.DestructiveRole
        )
        self.closeCancelButton = box.addButton(
            "Cancel", QMessageBox.ButtonRole.RejectRole
        )
        box.setDefaultButton(self.closeOkButton)
        # Set explicitly: QMessageBox only picks an escape button by itself
        # when one carries RejectRole, so without this Escape and the dialog's
        # own X did nothing at all.
        box.setEscapeButton(self.closeCancelButton)
        return box

    def closeActionFor(self, clicked: object) -> str | None:
        """Map the clicked button to 'close', 'clearAndClose', or None."""
        if clicked is self.closeClearButton:
            return "clearAndClose"
        if clicked is self.closeOkButton:
            return "close"
        # Cancel, Escape, or the dialog's X: do not exit at all, so a mistaken
        # click on the window's X costs nothing.
        return None

    def askCloseAction(self) -> str | None:
        """'close', 'clearAndClose', or None to stay open."""
        box = self.buildCloseDialog()
        box.exec()
        return self.closeActionFor(box.clickedButton())

    def onExitAndClearAll(self) -> None:
        self.clearClipboardAndHistory()
        # Intent is already explicit; do not ask again on the way out.
        self._closeWithoutPrompt = True
        self.close()

    def closeEvent(self, event: QCloseEvent) -> None:
        if not self._closeWithoutPrompt:
            action = self.askCloseAction()
            if action is None:
                event.ignore()
                return
            if action == "clearAndClose":
                self.clearClipboardAndHistory()

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
