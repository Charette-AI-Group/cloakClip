"""Clipboard tab — one-click cloak/uncloak straight on the clipboard."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from cloakClip.services import clipboardService
from cloakClip.services.cryptoService import CryptoError, decryptText, encryptText

if TYPE_CHECKING:
    from cloakClip.ui.mainWindow import MainWindow


class ClipboardTab(QWidget):
    def __init__(self, window: MainWindow) -> None:
        super().__init__()
        self.window = window

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Clipboard content:"))

        self.previewEdit = QPlainTextEdit()
        self.previewEdit.setReadOnly(True)
        self.previewEdit.setPlaceholderText("Clipboard is empty — copy some text (Ctrl+C).")
        layout.addWidget(self.previewEdit)

        buttonRow = QHBoxLayout()
        self.cloakButton = QPushButton("Cloak Clipboard")
        self.uncloakButton = QPushButton("Uncloak Clipboard")
        self.clearButton = QPushButton("Clear Clipboard && History")
        buttonRow.addWidget(self.cloakButton)
        buttonRow.addWidget(self.uncloakButton)
        buttonRow.addWidget(self.clearButton)
        layout.addLayout(buttonRow)

        self.cloakButton.clicked.connect(self.onCloakClicked)
        self.uncloakButton.clicked.connect(self.onUncloakClicked)
        self.clearButton.clicked.connect(self.window.clearClipboardAndHistory)
        QGuiApplication.clipboard().dataChanged.connect(self.refreshPreview)
        self.refreshPreview()

    def refreshPreview(self) -> None:
        self.previewEdit.setPlainText(clipboardService.readText())

    def onCloakClicked(self) -> None:
        text = clipboardService.readText()
        if not text:
            self.window.statusMessage("Clipboard is empty — copy some text first.")
            return
        password = self.window.ensurePassword()
        if password is None:
            return
        # Cloaked text is encrypted, so writing it plainly costs nothing.
        if self.window.writeClipboard(encryptText(text, password), secret=False):
            self.window.rememberActivePassword()
            self.window.statusMessage("Clipboard cloaked — paste the encrypted text anywhere.")

    def onUncloakClicked(self) -> None:
        text = clipboardService.readText()
        if not text:
            self.window.statusMessage("Clipboard is empty — copy an encrypted text first.")
            return
        password = self.window.ensurePassword()
        if password is None:
            return
        try:
            plainText = decryptText(text, password)
        except CryptoError as exc:
            self.window.statusMessage(str(exc))
            return
        # The plain text goes back on the clipboard (that is this tab's whole
        # point) but marked secret: out of Win+V history, cleared on exit.
        self.window.registerSecret(plainText)
        if self.window.writeClipboard(plainText, secret=True):
            self.window.rememberActivePassword()
            self.window.statusMessage(
                "Clipboard uncloaked — kept out of clipboard history, "
                "and cleared when you close CloakClip."
            )
