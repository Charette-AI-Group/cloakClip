"""Main application window — cloak/uncloak the clipboard."""

from __future__ import annotations

import datetime

from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from cloakClip import appConfig
from cloakClip.services.cryptoService import CryptoError, decryptText, encryptText


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(appConfig.windowTitle)
        self.resize(appConfig.defaultWindowWidth, appConfig.defaultWindowHeight)

        self.buildMenuBar()
        self.statusBar().showMessage("Ready")

        centralWidget = QWidget()
        layout = QVBoxLayout(centralWidget)

        layout.addWidget(QLabel("Clipboard content:"))
        self.clipboardPreview = QPlainTextEdit()
        self.clipboardPreview.setReadOnly(True)
        self.clipboardPreview.setPlaceholderText("Clipboard is empty — copy some text (Ctrl+C).")
        layout.addWidget(self.clipboardPreview)

        passwordRow = QHBoxLayout()
        passwordRow.addWidget(QLabel("Password:"))
        self.passwordEdit = QLineEdit()
        self.passwordEdit.setEchoMode(QLineEdit.EchoMode.Password)
        self.passwordEdit.setPlaceholderText("Shared password (12+ characters recommended)")
        passwordRow.addWidget(self.passwordEdit, stretch=1)
        self.showPasswordCheck = QCheckBox("Show")
        passwordRow.addWidget(self.showPasswordCheck)
        layout.addLayout(passwordRow)

        buttonRow = QHBoxLayout()
        self.cloakButton = QPushButton("Cloak Clipboard")
        self.uncloakButton = QPushButton("Uncloak Clipboard")
        self.clearButton = QPushButton("Clear Clipboard")
        buttonRow.addWidget(self.cloakButton)
        buttonRow.addWidget(self.uncloakButton)
        buttonRow.addWidget(self.clearButton)
        layout.addLayout(buttonRow)

        self.setCentralWidget(centralWidget)
        self._connectSignals()
        self.refreshPreview()

    def _connectSignals(self) -> None:
        self.cloakButton.clicked.connect(self.onCloakClicked)
        self.uncloakButton.clicked.connect(self.onUncloakClicked)
        self.clearButton.clicked.connect(self.onClearClicked)
        self.showPasswordCheck.toggled.connect(self.onShowPasswordToggled)
        QApplication.clipboard().dataChanged.connect(self.refreshPreview)

    def buildMenuBar(self) -> None:
        # Menus are kept as attributes: features can extend them later, and it
        # prevents the Python wrappers from being garbage-collected.
        fileMenu = self.fileMenu = self.menuBar().addMenu("&File")

        self.exitAction = QAction("E&xit", self)
        self.exitAction.setShortcut(QKeySequence("Ctrl+Q"))
        self.exitAction.triggered.connect(self.close)
        fileMenu.addAction(self.exitAction)

        helpMenu = self.helpMenu = self.menuBar().addMenu("&Help")

        self.aboutAction = QAction("&About", self)
        self.aboutAction.triggered.connect(self.onHelpAbout)
        helpMenu.addAction(self.aboutAction)

    def refreshPreview(self) -> None:
        self.clipboardPreview.setPlainText(QApplication.clipboard().text())

    def writeClipboard(self, text: str) -> bool:
        # The Windows clipboard is shared; writes fail when another process
        # briefly holds it. Verify the write and retry before giving up.
        clipboard = QApplication.clipboard()
        for _ in range(3):
            clipboard.setText(text)
            if clipboard.text() == text:
                return True
        self.statusBar().showMessage("The clipboard is busy — please try again.")
        return False

    def checkedPassword(self) -> str | None:
        password = self.passwordEdit.text()
        if not password:
            self.statusBar().showMessage("Enter a password first.")
            self.passwordEdit.setFocus()
            return None
        return password

    def onCloakClicked(self) -> None:
        text = QApplication.clipboard().text()
        if not text:
            self.statusBar().showMessage("Clipboard is empty — copy some text first.")
            return
        password = self.checkedPassword()
        if password is None:
            return
        if self.writeClipboard(encryptText(text, password)):
            self.statusBar().showMessage("Clipboard cloaked — paste the encrypted text anywhere.")

    def onUncloakClicked(self) -> None:
        text = QApplication.clipboard().text()
        if not text:
            self.statusBar().showMessage("Clipboard is empty — copy an encrypted text first.")
            return
        password = self.checkedPassword()
        if password is None:
            return
        try:
            plainText = decryptText(text, password)
        except CryptoError as exc:
            self.statusBar().showMessage(str(exc))
            return
        if self.writeClipboard(plainText):
            self.statusBar().showMessage("Clipboard uncloaked — the original is ready to paste.")

    def onClearClicked(self) -> None:
        if self.writeClipboard(""):
            self.statusBar().showMessage("Clipboard cleared.")

    def onShowPasswordToggled(self, checked: bool) -> None:
        echoMode = QLineEdit.EchoMode.Normal if checked else QLineEdit.EchoMode.Password
        self.passwordEdit.setEchoMode(echoMode)

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
