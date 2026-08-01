"""Modal dialog for entering a new password."""

from __future__ import annotations

from functools import partial

from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from cloakClip.services import passwordHistoryService


class PasswordDialog(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Enter Password")
        self.chosenPassword: str | None = None
        self.lastPasswordButton: QPushButton | None = None

        layout = QVBoxLayout(self)

        passwordRow = QHBoxLayout()
        passwordRow.addWidget(QLabel("Password:"))
        self.passwordEdit = QLineEdit()
        self.passwordEdit.setEchoMode(QLineEdit.EchoMode.Password)
        self.passwordEdit.setPlaceholderText("Shared password (12+ characters recommended)")
        self.passwordEdit.setMinimumWidth(320)
        passwordRow.addWidget(self.passwordEdit, stretch=1)
        layout.addLayout(passwordRow)

        self.showPasswordCheck = QCheckBox("Show password")
        self.showPasswordCheck.toggled.connect(self.onShowPasswordToggled)
        layout.addWidget(self.showPasswordCheck)

        passwords = passwordHistoryService.loadPasswords()
        if passwords:
            mask = passwordHistoryService.maskPassword(passwords[0])
            self.lastPasswordButton = QPushButton(f"Use Last Password ({mask})")
            self.lastPasswordButton.clicked.connect(partial(self.onUseLastPassword, passwords[0]))
            layout.addWidget(self.lastPasswordButton)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.okButton = buttons.button(QDialogButtonBox.StandardButton.Ok)
        self.okButton.setEnabled(False)
        self.passwordEdit.textChanged.connect(
            lambda text: self.okButton.setEnabled(bool(text))
        )

    def onShowPasswordToggled(self, checked: bool) -> None:
        echoMode = QLineEdit.EchoMode.Normal if checked else QLineEdit.EchoMode.Password
        self.passwordEdit.setEchoMode(echoMode)

    def onUseLastPassword(self, password: str) -> None:
        self.chosenPassword = password
        self.accept()

    def password(self) -> str:
        return self.chosenPassword or self.passwordEdit.text()

    @staticmethod
    def getPassword(parent: QWidget | None = None) -> str | None:
        dialog = PasswordDialog(parent)
        if dialog.exec() == QDialog.DialogCode.Accepted and dialog.password():
            return dialog.password()
        return None
