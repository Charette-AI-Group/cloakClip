"""Tests for the main window cloak/uncloak workflow.

clearHistory is always monkeypatched: the real call would wipe the Win+V
history of whoever runs the suite.
"""

from __future__ import annotations

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLineEdit

from cloakClip.services import clipboardService
from cloakClip.services.cryptoService import decryptText, encryptText
from cloakClip.ui.mainWindow import MainWindow


def setClipboard(qtbot, text: str) -> None:
    # The shared OS clipboard can be held by another process; keep trying.
    qtbot.waitUntil(lambda: clipboardService.writeText(text), timeout=5000)


@pytest.fixture
def historyCalls(monkeypatch) -> list[bool]:
    calls: list[bool] = []

    def fakeClearHistory() -> bool:
        calls.append(True)
        return True

    monkeypatch.setattr(clipboardService, "clearHistory", fakeClearHistory)
    return calls


@pytest.fixture
def window(qtbot, historyCalls) -> MainWindow:
    mainWindow = MainWindow()
    qtbot.addWidget(mainWindow)
    mainWindow.show()
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


def testCloakShowsResultAndCopiesIt(window, qtbot) -> None:
    window.inputEdit.setPlainText("my secret note")
    window.passwordEdit.setText("hunter2!")

    qtbot.mouseClick(window.cloakButton, Qt.MouseButton.LeftButton)

    cloaked = window.outputEdit.toPlainText()
    assert decryptText(cloaked, "hunter2!") == "my secret note"
    qtbot.waitUntil(lambda: clipboardService.readText() == cloaked, timeout=5000)
    assert "Cloaked and copied" in window.statusBar().currentMessage()


def testUncloakShowsPlainTextWithoutTouchingClipboard(window, qtbot) -> None:
    cloaked = encryptText("the original", "pw123")
    setClipboard(qtbot, cloaked)
    window.inputEdit.setPlainText(cloaked)
    window.passwordEdit.setText("pw123")

    qtbot.mouseClick(window.uncloakButton, Qt.MouseButton.LeftButton)

    assert window.outputEdit.toPlainText() == "the original"
    # The whole point: the secret is on screen but never on the clipboard.
    assert clipboardService.readText() == cloaked
    assert "click Copy" in window.statusBar().currentMessage()


def testUncloakWrongPasswordShowsError(window, qtbot) -> None:
    window.inputEdit.setPlainText(encryptText("the original", "right password"))
    window.passwordEdit.setText("wrong password")

    qtbot.mouseClick(window.uncloakButton, Qt.MouseButton.LeftButton)

    assert window.outputEdit.toPlainText() == ""
    assert "Wrong password" in window.statusBar().currentMessage()


def testCloakWithoutPasswordShowsHint(window, qtbot) -> None:
    window.inputEdit.setPlainText("something")

    qtbot.mouseClick(window.cloakButton, Qt.MouseButton.LeftButton)

    assert window.outputEdit.toPlainText() == ""
    assert window.statusBar().currentMessage() == "Enter a password first."


def testCloakWithEmptyInputShowsHint(window, qtbot) -> None:
    window.inputEdit.setPlainText("")
    window.passwordEdit.setText("pw")

    qtbot.mouseClick(window.cloakButton, Qt.MouseButton.LeftButton)

    assert "Nothing to cloak" in window.statusBar().currentMessage()


def testCopyPutsUncloakedResultOnClipboard(window, qtbot) -> None:
    window.inputEdit.setPlainText(encryptText("copy me", "pw"))
    window.passwordEdit.setText("pw")
    qtbot.mouseClick(window.uncloakButton, Qt.MouseButton.LeftButton)

    qtbot.mouseClick(window.copyButton, Qt.MouseButton.LeftButton)

    qtbot.waitUntil(lambda: clipboardService.readText() == "copy me", timeout=5000)
    assert "kept out of clipboard history" in window.statusBar().currentMessage()


def testCopyWithoutResultShowsHint(window, qtbot) -> None:
    qtbot.mouseClick(window.copyButton, Qt.MouseButton.LeftButton)

    assert window.statusBar().currentMessage() == "There is no result to copy yet."


def testPasteLoadsClipboardIntoInput(window, qtbot) -> None:
    setClipboard(qtbot, "pasted content")
    window.inputEdit.setPlainText("")

    qtbot.mouseClick(window.pasteButton, Qt.MouseButton.LeftButton)

    assert window.inputEdit.toPlainText() == "pasted content"


def testCopyingElsewhereFillsInput(window, qtbot) -> None:
    setClipboard(qtbot, "copied somewhere else")

    qtbot.waitUntil(
        lambda: window.inputEdit.toPlainText() == "copied somewhere else", timeout=5000
    )


def testClearEmptiesClipboardAndHistory(window, qtbot, historyCalls) -> None:
    setClipboard(qtbot, "leftover secret")
    window.outputEdit.setPlainText("leftover result")

    def clearSucceeded() -> bool:
        window.clearButton.click()
        return clipboardService.readText() == ""

    qtbot.waitUntil(clearSucceeded, timeout=5000)

    assert window.outputEdit.toPlainText() == ""
    assert historyCalls, "the Clear button must purge clipboard history too"
    assert window.statusBar().currentMessage() == "Clipboard and clipboard history cleared."


def testClosingClearsAnUncloakedSecret(window, qtbot) -> None:
    window.inputEdit.setPlainText(encryptText("sensitive", "pw"))
    window.passwordEdit.setText("pw")
    qtbot.mouseClick(window.uncloakButton, Qt.MouseButton.LeftButton)
    qtbot.mouseClick(window.copyButton, Qt.MouseButton.LeftButton)
    qtbot.waitUntil(lambda: clipboardService.readText() == "sensitive", timeout=5000)

    window.close()

    assert clipboardService.readText() == ""


def testClosingKeepsCloakedTextPasteable(window, qtbot) -> None:
    window.inputEdit.setPlainText("not secret once encrypted")
    window.passwordEdit.setText("pw")
    qtbot.mouseClick(window.cloakButton, Qt.MouseButton.LeftButton)
    cloaked = window.outputEdit.toPlainText()
    qtbot.waitUntil(lambda: clipboardService.readText() == cloaked, timeout=5000)

    window.close()

    assert clipboardService.readText() == cloaked


def testClosingLeavesUnrelatedClipboardAlone(window, qtbot) -> None:
    setClipboard(qtbot, "the user's own clipboard content")

    window.close()

    assert clipboardService.readText() == "the user's own clipboard content"


def testShowPasswordToggle(window) -> None:
    assert window.passwordEdit.echoMode() == QLineEdit.EchoMode.Password
    window.showPasswordCheck.setChecked(True)
    assert window.passwordEdit.echoMode() == QLineEdit.EchoMode.Normal
    window.showPasswordCheck.setChecked(False)
    assert window.passwordEdit.echoMode() == QLineEdit.EchoMode.Password


def testAboutTextContents(window) -> None:
    aboutText = window.buildAboutText()

    assert "CloakClip" in aboutText
    assert "Editor: Francois Charette, PhD" in aboutText
    assert "AI Agent: Claude - Fable 5" in aboutText
    assert "Charette AI Group, LLC" in aboutText
