"""Tests for the password entry dialog."""

from __future__ import annotations

from PySide6.QtWidgets import QLineEdit

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
