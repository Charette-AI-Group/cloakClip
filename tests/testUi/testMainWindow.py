"""Tests for the main window cloak/uncloak workflow."""

from __future__ import annotations

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QLineEdit

from cloakClip.services.cryptoService import CryptoError, decryptText, encryptText
from cloakClip.ui.mainWindow import MainWindow


def setClipboard(qtbot, text: str) -> None:
    # The Windows clipboard is a shared OS resource; setText can fail when
    # another process briefly holds it, so retry until the write sticks.
    clipboard = QApplication.clipboard()

    def writeStuck() -> bool:
        clipboard.setText(text)
        return clipboard.text() == text

    qtbot.waitUntil(writeStuck, timeout=2000)


@pytest.fixture
def window(qtbot) -> MainWindow:
    mainWindow = MainWindow()
    qtbot.addWidget(mainWindow)
    mainWindow.show()
    setClipboard(qtbot, "")
    return mainWindow


def testMainWindowOpens(window) -> None:
    assert window.isVisible()
    assert window.windowTitle() == "CloakClip"
    assert window.statusBar().currentMessage() == "Ready"


def testMenuBarStructure(window) -> None:
    menuTitles = [action.text() for action in window.menuBar().actions()]
    assert menuTitles == ["&File", "&Help"]
    assert [a.text() for a in window.fileMenu.actions()] == ["E&xit"]
    assert [a.text() for a in window.helpMenu.actions()] == ["&About"]


def testCloakReplacesClipboardWithDecryptableText(window, qtbot) -> None:
    window.passwordEdit.setText("hunter2!")

    # Reset state and retry the whole operation: the shared OS clipboard can
    # reject individual writes while another process holds it.
    def cloakSucceeded() -> bool:
        setClipboard(qtbot, "my secret note")
        qtbot.mouseClick(window.cloakButton, Qt.MouseButton.LeftButton)
        try:
            cloaked = QApplication.clipboard().text()
            return decryptText(cloaked, "hunter2!") == "my secret note"
        except CryptoError:
            return False

    qtbot.waitUntil(cloakSucceeded, timeout=5000)
    assert QApplication.clipboard().text() != "my secret note"
    assert "cloaked" in window.statusBar().currentMessage()


def testUncloakRestoresOriginalText(window, qtbot) -> None:
    cloaked = encryptText("the original", "pw123")
    window.passwordEdit.setText("pw123")

    def uncloakSucceeded() -> bool:
        setClipboard(qtbot, cloaked)
        qtbot.mouseClick(window.uncloakButton, Qt.MouseButton.LeftButton)
        return QApplication.clipboard().text() == "the original"

    qtbot.waitUntil(uncloakSucceeded, timeout=5000)
    assert "uncloaked" in window.statusBar().currentMessage()


def testUncloakWrongPasswordLeavesClipboardUntouched(window, qtbot) -> None:
    cloaked = encryptText("the original", "right password")
    setClipboard(qtbot, cloaked)
    window.passwordEdit.setText("wrong password")

    qtbot.mouseClick(window.uncloakButton, Qt.MouseButton.LeftButton)

    assert QApplication.clipboard().text() == cloaked
    assert "Wrong password" in window.statusBar().currentMessage()


def testCloakWithoutPasswordShowsHint(window, qtbot) -> None:
    setClipboard(qtbot, "something")

    qtbot.mouseClick(window.cloakButton, Qt.MouseButton.LeftButton)

    assert QApplication.clipboard().text() == "something"
    assert window.statusBar().currentMessage() == "Enter a password first."


def testCloakWithEmptyClipboardShowsHint(window, qtbot) -> None:
    window.passwordEdit.setText("pw")

    qtbot.mouseClick(window.cloakButton, Qt.MouseButton.LeftButton)

    assert "Clipboard is empty" in window.statusBar().currentMessage()


def testClearButtonEmptiesClipboard(window, qtbot) -> None:
    def clearSucceeded() -> bool:
        setClipboard(qtbot, "leftover secret")
        qtbot.mouseClick(window.clearButton, Qt.MouseButton.LeftButton)
        return QApplication.clipboard().text() == ""

    qtbot.waitUntil(clearSucceeded, timeout=5000)
    assert window.statusBar().currentMessage() == "Clipboard cleared."


def testPreviewFollowsClipboard(window, qtbot) -> None:
    setClipboard(qtbot, "watch me appear")
    qtbot.waitUntil(lambda: window.clipboardPreview.toPlainText() == "watch me appear")


def testShowPasswordToggle(window) -> None:
    assert window.passwordEdit.echoMode() == QLineEdit.EchoMode.Password
    window.showPasswordCheck.setChecked(True)
    assert window.passwordEdit.echoMode() == QLineEdit.EchoMode.Normal
    window.showPasswordCheck.setChecked(False)
    assert window.passwordEdit.echoMode() == QLineEdit.EchoMode.Password


def testAboutTextContents(window) -> None:
    aboutText = window.buildAboutText()
    assert "CloakClip" in aboutText
    assert "Editor: Francois Charette" in aboutText
    assert "AI Agent: Claude - Fable 5" in aboutText
    assert "Charette AI Group, LLC" in aboutText
