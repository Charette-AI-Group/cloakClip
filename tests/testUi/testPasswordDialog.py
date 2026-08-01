"""Tests for the password entry dialog."""

from __future__ import annotations

from PySide6.QtWidgets import QDialog, QLineEdit

from cloakClip.services import passwordHistoryService
from cloakClip.ui.dialogs.passwordDialog import PasswordDialog


def testPasswordIsMaskedByDefault(qtbot) -> None:
    dialog = PasswordDialog()
    qtbot.addWidget(dialog)

    assert dialog.passwordEdit.echoMode() == QLineEdit.EchoMode.Password


def testShowPasswordToggle(qtbot) -> None:
    dialog = PasswordDialog()
    qtbot.addWidget(dialog)

    dialog.showPasswordCheck.setChecked(True)
    assert dialog.passwordEdit.echoMode() == QLineEdit.EchoMode.Normal
    dialog.showPasswordCheck.setChecked(False)
    assert dialog.passwordEdit.echoMode() == QLineEdit.EchoMode.Password


def testOkDisabledUntilPasswordTyped(qtbot) -> None:
    dialog = PasswordDialog()
    qtbot.addWidget(dialog)

    assert not dialog.okButton.isEnabled()
    dialog.passwordEdit.setText("something")
    assert dialog.okButton.isEnabled()
    dialog.passwordEdit.setText("")
    assert not dialog.okButton.isEnabled()


def testPasswordReturnsTypedText(qtbot) -> None:
    dialog = PasswordDialog()
    qtbot.addWidget(dialog)

    dialog.passwordEdit.setText("hunter2!")
    assert dialog.password() == "hunter2!"


def testNoLastPasswordButtonWithoutHistory(qtbot) -> None:
    dialog = PasswordDialog()
    qtbot.addWidget(dialog)

    assert dialog.lastPasswordButton is None


def testUseLastPasswordButtonAcceptsWithLastPassword(qtbot) -> None:
    passwordHistoryService.rememberPassword("older-password!")
    passwordHistoryService.rememberPassword("hunter2!")
    dialog = PasswordDialog()
    qtbot.addWidget(dialog)

    assert dialog.lastPasswordButton is not None
    assert dialog.lastPasswordButton.text() == "Use Last Password (h...!)"
    # Only the mask is shown — never the full password.
    assert "hunter2!" not in dialog.lastPasswordButton.text()

    dialog.lastPasswordButton.click()

    assert dialog.result() == QDialog.DialogCode.Accepted
    assert dialog.password() == "hunter2!"
