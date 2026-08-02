"""Manual tab — plain and cloaked fields that stay in sync live.

Editing the plain-text field re-encrypts it into the cloaked field after a
short pause; pasting (or editing) a cloaked string decrypts it into the
plain-text field. No buttons to click for either direction.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import QTimer
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

syncDelayMs = 300


class ManualTab(QWidget):
    def __init__(self, window: MainWindow) -> None:
        super().__init__()
        self.window = window
        # True while this tab writes to its own fields, so the resulting
        # textChanged signals are not mistaken for user edits (which would
        # ping-pong forever, since every encryption has a fresh IV).
        self._syncing = False
        # Which field the user last edited — the sync source of truth.
        self._lastSource: str | None = None

        layout = QVBoxLayout(self)

        plainHeader = QHBoxLayout()
        plainHeader.addWidget(QLabel("Plain text (uncloaked):"))
        plainHeader.addStretch()
        self.plainPasteButton = QPushButton("Paste")
        self.plainCopyButton = QPushButton("Copy")
        plainHeader.addWidget(self.plainPasteButton)
        plainHeader.addWidget(self.plainCopyButton)
        layout.addLayout(plainHeader)

        self.plainEdit = QPlainTextEdit()
        self.plainEdit.setPlaceholderText(
            "Type the text to protect here — the cloaked version appears below as you type."
        )
        layout.addWidget(self.plainEdit)

        cloakHeader = QHBoxLayout()
        cloakHeader.addWidget(QLabel("Encrypted (cloaked):"))
        cloakHeader.addStretch()
        self.cloakPasteButton = QPushButton("Paste")
        self.cloakCopyButton = QPushButton("Copy")
        cloakHeader.addWidget(self.cloakPasteButton)
        cloakHeader.addWidget(self.cloakCopyButton)
        layout.addLayout(cloakHeader)

        self.cloakEdit = QPlainTextEdit()
        self.cloakEdit.setPlaceholderText(
            "Paste an encrypted text here — it uncloaks above automatically."
        )
        layout.addWidget(self.cloakEdit)

        self.syncTimer = QTimer(self)
        self.syncTimer.setSingleShot(True)
        self.syncTimer.setInterval(syncDelayMs)
        self.syncTimer.timeout.connect(self.syncNow)

        self.plainEdit.textChanged.connect(self.onPlainEdited)
        self.cloakEdit.textChanged.connect(self.onCloakEdited)
        self.plainCopyButton.clicked.connect(self.onPlainCopyClicked)
        self.plainPasteButton.clicked.connect(self.onPlainPasteClicked)
        self.cloakCopyButton.clicked.connect(self.onCloakCopyClicked)
        self.cloakPasteButton.clicked.connect(self.onCloakPasteClicked)

    # ------------------------------------------------------------- syncing

    def onPlainEdited(self) -> None:
        if self._syncing:
            return
        self._lastSource = "plain"
        self.syncTimer.start()

    def onCloakEdited(self) -> None:
        if self._syncing:
            return
        self._lastSource = "cloak"
        self.syncTimer.start()

    def onPasswordActivated(self) -> None:
        # A password became active; run the sync that was waiting for one.
        if self._lastSource is None:
            if self.plainEdit.toPlainText():
                self._lastSource = "plain"
            elif self.cloakEdit.toPlainText():
                self._lastSource = "cloak"
        if self._lastSource is not None:
            self.syncTimer.start()

    def setFieldText(self, field: QPlainTextEdit, text: str) -> None:
        self._syncing = True
        try:
            field.setPlainText(text)
        finally:
            self._syncing = False

    def syncNow(self) -> None:
        if self._lastSource == "plain":
            self.encryptFromPlain()
        elif self._lastSource == "cloak":
            self.decryptFromCloak()

    def encryptFromPlain(self) -> None:
        text = self.plainEdit.toPlainText()
        if not text:
            self.setFieldText(self.cloakEdit, "")
            return
        password = self.window.activePassword
        if not password:
            self.window.statusMessage("Select a password (Ctrl+P) to start cloaking.")
            return
        self.setFieldText(self.cloakEdit, encryptText(text, password))
        self.window.statusMessage("Cloaked below — updates live as you type.")

    def decryptFromCloak(self) -> None:
        text = self.cloakEdit.toPlainText()
        if not text:
            self.setFieldText(self.plainEdit, "")
            return
        password = self.window.activePassword
        if not password:
            self.window.statusMessage("Select a password (Ctrl+P) to uncloak.")
            return
        try:
            plainText = decryptText(text.strip(), password)
        except CryptoError:
            self.setFieldText(self.plainEdit, "")
            self.window.statusMessage(
                "Not a complete cloaked text yet — or not the right password."
            )
            return
        # On-screen only; registered so manual re-copies of it stay protected.
        self.window.registerSecret(plainText)
        self.window.rememberActivePassword()
        self.setFieldText(self.plainEdit, plainText)
        self.window.statusMessage("Uncloaked above — click its Copy only if you need to paste it.")

    def clearFields(self) -> None:
        self.syncTimer.stop()
        self._lastSource = None
        self.setFieldText(self.plainEdit, "")
        self.setFieldText(self.cloakEdit, "")

    # ------------------------------------------------------------- buttons

    def onPlainCopyClicked(self) -> None:
        text = self.plainEdit.toPlainText()
        if not text:
            self.window.statusMessage("There is no plain text to copy.")
            return
        self.window.registerSecret(text)
        if self.window.writeClipboard(text, secret=True):
            self.window.statusMessage(
                "Copied — kept out of clipboard history, and cleared when you close CloakClip."
            )

    def onCloakCopyClicked(self) -> None:
        text = self.cloakEdit.toPlainText()
        if not text:
            self.window.statusMessage("There is no cloaked text to copy.")
            return
        if self.window.writeClipboard(text, secret=False):
            self.window.rememberActivePassword()
            self.window.statusMessage("Copied — paste it anywhere.")

    def onPlainPasteClicked(self) -> None:
        self.plainEdit.setPlainText(clipboardService.readText())
        self.window.statusMessage("Pasted — cloaking...")

    def onCloakPasteClicked(self) -> None:
        self.cloakEdit.setPlainText(clipboardService.readText())
        self.window.statusMessage("Pasted — uncloaking...")
