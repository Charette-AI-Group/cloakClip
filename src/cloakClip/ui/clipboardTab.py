"""Clipboard tab — cloak/uncloak straight on the clipboard, and edit in place."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import QTimer
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

editDelayMs = 300


class ClipboardTab(QWidget):
    def __init__(self, window: MainWindow) -> None:
        super().__init__()
        self.window = window
        # True while this tab writes to its own box, so the resulting
        # textChanged is not mistaken for the user typing.
        self._syncing = False
        # Set only by a real user edit. Everything keys off this rather than
        # off "preview differs from clipboard", which would mistake a preview
        # that has not caught up yet for something the user typed.
        self._pendingEdit = False
        # Whether what is shown is decrypted plain text. Edits to it must be
        # written back marked secret, exactly as the uncloak itself was.
        self.contentIsSecret = False

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Clipboard content (editable):"))

        self.previewEdit = QPlainTextEdit()
        self.previewEdit.setPlaceholderText(
            "Copy some text (Ctrl+C) — it appears here, and you can edit it."
        )
        layout.addWidget(self.previewEdit)

        buttonRow = QHBoxLayout()
        self.cloakButton = QPushButton("Cloak Clipboard")
        self.uncloakButton = QPushButton("Uncloak Clipboard")
        self.clearButton = QPushButton("Clear Clipboard && History")
        buttonRow.addWidget(self.cloakButton)
        buttonRow.addWidget(self.uncloakButton)
        buttonRow.addWidget(self.clearButton)
        layout.addLayout(buttonRow)

        self.editTimer = QTimer(self)
        self.editTimer.setSingleShot(True)
        self.editTimer.setInterval(editDelayMs)
        self.editTimer.timeout.connect(self.flushEdit)

        self.cloakButton.clicked.connect(self.onCloakClicked)
        self.uncloakButton.clicked.connect(self.onUncloakClicked)
        self.clearButton.clicked.connect(self.window.clearClipboardAndHistory)
        self.previewEdit.textChanged.connect(self.onPreviewEdited)
        QGuiApplication.clipboard().dataChanged.connect(self.refreshPreview)
        self.refreshPreview()

    # ------------------------------------------------------------- editing

    def setPreviewText(self, text: str) -> None:
        self._syncing = True
        try:
            self.previewEdit.setPlainText(text)
            self._pendingEdit = False
        finally:
            self._syncing = False

    def refreshPreview(self) -> None:
        if self._syncing:
            return
        # Never overwrite an edit that has not been pushed out yet. Focus is
        # deliberately not the test: the box is the first focusable widget, so
        # keying off it would stop the preview ever following the clipboard.
        if self._pendingEdit:
            return
        # Never echo back a write this app just made; it would also reset the
        # cursor position mid-edit.
        text = clipboardService.readText()
        if text == self.window.lastClipboardWrite:
            return
        self.setPreviewText(text)
        # Content that arrived from elsewhere is not a known secret.
        self.contentIsSecret = False

    def onPreviewEdited(self) -> None:
        if self._syncing:
            return
        self._pendingEdit = True
        self.editTimer.start()

    def flushEdit(self) -> None:
        """Push a pending edit to the clipboard now."""
        self.editTimer.stop()
        if not self._pendingEdit:
            return
        self._pendingEdit = False
        text = self.previewEdit.toPlainText()
        if text == clipboardService.readText():
            return
        if not text:
            clipboardService.clearText()
            self.window.lastClipboardWrite = None
            self.window.lastWriteWasSecret = False
            return
        if self.contentIsSecret:
            self.window.registerSecret(text)
        if self.window.writeClipboard(text, secret=self.contentIsSecret):
            self.window.statusMessage(
                "Edit copied to the clipboard — click Cloak Clipboard when done."
                if self.contentIsSecret
                else "Edit copied to the clipboard."
            )

    def clearPreview(self) -> None:
        self.editTimer.stop()
        self.contentIsSecret = False
        self.setPreviewText("")

    def currentText(self) -> str:
        """The text to act on: a pending edit if there is one, else the clipboard."""
        if self._pendingEdit:
            self.flushEdit()
            return self.previewEdit.toPlainText()
        # No edit in progress, so the clipboard is authoritative — the preview
        # may simply not have been told about a change yet.
        text = clipboardService.readText()
        if text != self.previewEdit.toPlainText():
            self.setPreviewText(text)
        return text

    # ------------------------------------------------------------- actions

    def onCloakClicked(self) -> None:
        text = self.currentText()
        if not text:
            self.window.statusMessage("Clipboard is empty — copy some text first.")
            return
        password = self.window.ensurePassword()
        if password is None:
            return
        # Whatever you asked to cloak was worth protecting, and whichever app
        # you copied it from already recorded it in clipboard history without
        # any marking. Tracking it gets it swept out on the way out.
        self.window.registerSecret(text)
        cloaked = encryptText(text, password)
        self.contentIsSecret = False
        # Cloaked text is encrypted, so writing it plainly costs nothing.
        if self.window.writeClipboard(cloaked, secret=False):
            self.setPreviewText(cloaked)
            self.window.rememberActivePassword()
            self.window.statusMessage("Clipboard cloaked — paste the encrypted text anywhere.")

    def onUncloakClicked(self) -> None:
        text = self.currentText()
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
            self.contentIsSecret = True
            self.setPreviewText(plainText)
            self.window.rememberActivePassword()
            self.window.statusMessage(
                "Uncloaked and kept out of clipboard history — "
                "edit it here if you like, then click Cloak Clipboard."
            )
