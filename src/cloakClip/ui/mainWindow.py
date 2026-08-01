"""Main application window — cloak and uncloak text."""

from __future__ import annotations

import datetime
from functools import partial

from PySide6.QtGui import QAction, QCloseEvent, QGuiApplication, QKeySequence
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from cloakClip import appConfig
from cloakClip.services import clipboardService, passwordHistoryService
from cloakClip.services.cryptoService import CryptoError, decryptText, encryptText
from cloakClip.ui.dialogs.passwordDialog import PasswordDialog


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(appConfig.windowTitle)
        self.resize(appConfig.defaultWindowWidth, appConfig.defaultWindowHeight)

        # Remember what CloakClip itself put on the clipboard, so it can tell
        # its own writes from the user's copies and clean up secrets on exit.
        self.lastClipboardWrite: str | None = None
        self.lastWriteWasSecret = False
        self.resultIsSecret = False
        self.activePassword: str | None = None

        self.buildMenuBar()
        self.buildCentralWidget()
        self._connectSignals()

        self.inputEdit.setPlainText(clipboardService.readText())
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

    def buildCentralWidget(self) -> None:
        centralWidget = QWidget()
        layout = QVBoxLayout(centralWidget)

        inputHeader = QHBoxLayout()
        inputHeader.addWidget(QLabel("Text to cloak or uncloak:"))
        inputHeader.addStretch()
        self.pasteButton = QPushButton("Paste")
        inputHeader.addWidget(self.pasteButton)
        layout.addLayout(inputHeader)

        self.inputEdit = QPlainTextEdit()
        self.inputEdit.setPlaceholderText(
            "Type here, or copy text anywhere and it appears automatically."
        )
        layout.addWidget(self.inputEdit)

        actionRow = QHBoxLayout()
        self.cloakButton = QPushButton("Cloak")
        self.uncloakButton = QPushButton("Uncloak")
        actionRow.addWidget(self.cloakButton)
        actionRow.addWidget(self.uncloakButton)
        layout.addLayout(actionRow)

        resultHeader = QHBoxLayout()
        resultHeader.addWidget(QLabel("Result:"))
        resultHeader.addStretch()
        self.copyButton = QPushButton("Copy")
        resultHeader.addWidget(self.copyButton)
        layout.addLayout(resultHeader)

        self.outputEdit = QPlainTextEdit()
        self.outputEdit.setReadOnly(True)
        self.outputEdit.setPlaceholderText("The cloaked or uncloaked text appears here.")
        layout.addWidget(self.outputEdit)

        self.clearButton = QPushButton("Clear Clipboard && History")
        layout.addWidget(self.clearButton)

        self.setCentralWidget(centralWidget)

        self.passwordLabel = QLabel("No password selected")
        self.statusBar().addPermanentWidget(self.passwordLabel)

    def _connectSignals(self) -> None:
        self.cloakButton.clicked.connect(self.onCloakClicked)
        self.uncloakButton.clicked.connect(self.onUncloakClicked)
        self.pasteButton.clicked.connect(self.onPasteClicked)
        self.copyButton.clicked.connect(self.onCopyClicked)
        self.clearButton.clicked.connect(self.onClearClicked)
        QGuiApplication.clipboard().dataChanged.connect(self.onClipboardChanged)

    def onClipboardChanged(self) -> None:
        # Follow the user's copies, but never overwrite what they are typing
        # or echo back what CloakClip just wrote itself.
        if self.inputEdit.hasFocus():
            return
        text = clipboardService.readText()
        if text == self.lastClipboardWrite:
            return
        self.inputEdit.setPlainText(text)

    # ------------------------------------------------------------ passwords

    def usePassword(self, password: str) -> None:
        self.activePassword = password
        mask = passwordHistoryService.maskPassword(password)
        self.passwordLabel.setText(f"Password: {mask}")
        self.statusBar().showMessage(f"Password {mask} selected.")

    def onNewPassword(self) -> None:
        password = PasswordDialog.getPassword(self)
        if password:
            self.usePassword(password)

    def onClearPasswordHistory(self) -> None:
        passwordHistoryService.clearPasswords()
        self.activePassword = None
        self.passwordLabel.setText("No password selected")
        self.statusBar().showMessage("Password history cleared.")

    def ensurePassword(self) -> str | None:
        if self.activePassword:
            return self.activePassword
        self.onNewPassword()
        if self.activePassword is None:
            self.statusBar().showMessage("Enter a password first (Password menu, Ctrl+P).")
        return self.activePassword

    def rememberActivePassword(self) -> None:
        if self.activePassword:
            passwordHistoryService.rememberPassword(self.activePassword)

    # ------------------------------------------------------------- actions

    def checkedInput(self, emptyMessage: str) -> str | None:
        text = self.inputEdit.toPlainText()
        if not text:
            self.statusBar().showMessage(emptyMessage)
            return None
        return text

    def writeClipboard(self, text: str, secret: bool) -> bool:
        if not clipboardService.writeText(text, secret=secret):
            self.statusBar().showMessage("The clipboard is busy — please try again.")
            return False
        self.lastClipboardWrite = text
        self.lastWriteWasSecret = secret
        return True

    def showResult(self, text: str, secret: bool) -> None:
        self.outputEdit.setPlainText(text)
        self.resultIsSecret = secret

    def onCloakClicked(self) -> None:
        text = self.checkedInput("Nothing to cloak — type or copy some text first.")
        if text is None:
            return
        password = self.ensurePassword()
        if password is None:
            return

        cloaked = encryptText(text, password)
        self.rememberActivePassword()
        self.showResult(cloaked, secret=False)
        # Cloaked text is encrypted, so putting it straight on the clipboard
        # costs nothing and keeps the original one-click flow.
        if self.writeClipboard(cloaked, secret=False):
            self.statusBar().showMessage("Cloaked and copied — paste it anywhere.")

    def onUncloakClicked(self) -> None:
        text = self.checkedInput("Nothing to uncloak — copy an encrypted text first.")
        if text is None:
            return
        password = self.ensurePassword()
        if password is None:
            return

        try:
            plainText = decryptText(text, password)
        except CryptoError as exc:
            self.statusBar().showMessage(str(exc))
            return

        self.rememberActivePassword()
        # Deliberately not copied: read it here and the secret never reaches
        # the clipboard at all.
        self.showResult(plainText, secret=True)
        self.statusBar().showMessage("Uncloaked below — click Copy only if you need to paste it.")

    def onPasteClicked(self) -> None:
        self.inputEdit.setPlainText(clipboardService.readText())
        self.statusBar().showMessage("Pasted from the clipboard.")

    def onCopyClicked(self) -> None:
        text = self.outputEdit.toPlainText()
        if not text:
            self.statusBar().showMessage("There is no result to copy yet.")
            return
        if not self.writeClipboard(text, secret=self.resultIsSecret):
            return
        if self.resultIsSecret:
            self.statusBar().showMessage(
                "Copied — kept out of clipboard history, and cleared when you close CloakClip."
            )
        else:
            self.statusBar().showMessage("Copied — paste it anywhere.")

    def onClearClicked(self) -> None:
        clipboardCleared = clipboardService.clearText()
        historyCleared = clipboardService.clearHistory()
        self.lastClipboardWrite = None
        self.lastWriteWasSecret = False
        self.outputEdit.clear()

        if not clipboardCleared:
            self.statusBar().showMessage("The clipboard is busy — please try again.")
        elif historyCleared:
            self.statusBar().showMessage("Clipboard and clipboard history cleared.")
        else:
            self.statusBar().showMessage("Clipboard cleared; clipboard history was unavailable.")

    def closeEvent(self, event: QCloseEvent) -> None:
        # Never leave an uncloaked secret behind. Cloaked text is harmless and
        # is left alone so it can still be pasted after the window closes.
        if self.lastWriteWasSecret and clipboardService.readText() == self.lastClipboardWrite:
            clipboardService.clearText()
        super().closeEvent(event)

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
