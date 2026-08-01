"""Manual tab — type or paste text, read the result, copy only on demand."""

from __future__ import annotations

from typing import TYPE_CHECKING

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


class ManualTab(QWidget):
    def __init__(self, window: MainWindow) -> None:
        super().__init__()
        self.window = window
        self.resultIsSecret = False

        layout = QVBoxLayout(self)

        inputHeader = QHBoxLayout()
        inputHeader.addWidget(QLabel("Text to cloak or uncloak:"))
        inputHeader.addStretch()
        self.pasteButton = QPushButton("Paste")
        inputHeader.addWidget(self.pasteButton)
        layout.addLayout(inputHeader)

        self.inputEdit = QPlainTextEdit()
        self.inputEdit.setPlaceholderText("Type here, or use Paste.")
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

        self.cloakButton.clicked.connect(self.onCloakClicked)
        self.uncloakButton.clicked.connect(self.onUncloakClicked)
        self.pasteButton.clicked.connect(self.onPasteClicked)
        self.copyButton.clicked.connect(self.onCopyClicked)

    def checkedInput(self, emptyMessage: str) -> str | None:
        text = self.inputEdit.toPlainText()
        if not text:
            self.window.statusMessage(emptyMessage)
            return None
        return text

    def showResult(self, text: str, secret: bool) -> None:
        self.outputEdit.setPlainText(text)
        self.resultIsSecret = secret

    def onCloakClicked(self) -> None:
        text = self.checkedInput("Nothing to cloak — type or paste some text first.")
        if text is None:
            return
        password = self.window.ensurePassword()
        if password is None:
            return
        self.window.rememberActivePassword()
        self.showResult(encryptText(text, password), secret=False)
        self.window.statusMessage("Cloaked — click Copy to put it on the clipboard.")

    def onUncloakClicked(self) -> None:
        text = self.checkedInput("Nothing to uncloak — paste an encrypted text first.")
        if text is None:
            return
        password = self.window.ensurePassword()
        if password is None:
            return
        try:
            plainText = decryptText(text, password)
        except CryptoError as exc:
            self.window.statusMessage(str(exc))
            return
        self.window.rememberActivePassword()
        # Deliberately not copied: read it here and the secret never reaches
        # the clipboard at all. Registered anyway, in case the user copies the
        # shown text by hand.
        self.window.registerSecret(plainText)
        self.showResult(plainText, secret=True)
        self.window.statusMessage("Uncloaked below — click Copy only if you need to paste it.")

    def onPasteClicked(self) -> None:
        self.inputEdit.setPlainText(clipboardService.readText())
        self.window.statusMessage("Pasted from the clipboard.")

    def onCopyClicked(self) -> None:
        text = self.outputEdit.toPlainText()
        if not text:
            self.window.statusMessage("There is no result to copy yet.")
            return
        if not self.window.writeClipboard(text, secret=self.resultIsSecret):
            return
        if self.resultIsSecret:
            self.window.statusMessage(
                "Copied — kept out of clipboard history, and cleared when you close CloakClip."
            )
        else:
            self.window.statusMessage("Copied — paste it anywhere.")
