"""Tests for the main window cloak/uncloak workflow.

clearHistory is always monkeypatched: the real call would wipe the Win+V
history of whoever runs the suite. The password history file is redirected
to a temp folder so tests never touch the real one.
"""

from __future__ import annotations

import pytest
from PySide6.QtCore import Qt

from cloakClip import appConfig
from cloakClip.services import clipboardService, passwordHistoryService
from cloakClip.services.cryptoService import decryptText, encryptText
from cloakClip.ui.dialogs.passwordDialog import PasswordDialog
from cloakClip.ui.mainWindow import MainWindow


def setClipboard(qtbot, text: str) -> None:
    # The shared OS clipboard can be held by another process; keep trying.
    qtbot.waitUntil(lambda: clipboardService.writeText(text), timeout=5000)


@pytest.fixture(autouse=True)
def isolatedPasswordHistory(tmp_path, monkeypatch):
    monkeypatch.setattr(appConfig, "passwordHistoryFile", tmp_path / "passwordHistory.bin")


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
    assert window.passwordLabel.text() == "No password selected"


def testMenuBarStructure(window) -> None:
    menuTitles = [action.text() for action in window.menuBar().actions()]
    assert menuTitles == ["&File", "&Password", "&Help"]
    assert [a.text() for a in window.fileMenu.actions()] == ["E&xit"]
    assert [a.text() for a in window.helpMenu.actions()] == ["&About"]


def testPasswordMenuEmptyState(window) -> None:
    window.rebuildPasswordMenu()
    itemTexts = [a.text() for a in window.passwordMenu.actions() if not a.isSeparator()]

    assert itemTexts == [
        "No Passwords Remembered Yet", "&New Password...", "Clear Password History",
    ]
    clearAction = window.passwordMenu.actions()[-1]
    assert not clearAction.isEnabled()


def testPasswordMenuListsMaskedHistory(window) -> None:
    passwordHistoryService.rememberPassword("older-password!")
    passwordHistoryService.rememberPassword("hunter2!")
    window.rebuildPasswordMenu()

    itemTexts = [a.text() for a in window.passwordMenu.actions() if not a.isSeparator()]
    assert itemTexts == [
        "Last Password Used (h...!)",
        "h...!",
        "o...!",
        "&New Password...",
        "Clear Password History",
    ]
    # Only masks appear — never a full password.
    assert all("hunter2!" not in text and "older-password!" not in text for text in itemTexts)


def testPickingMenuEntrySelectsPassword(window) -> None:
    passwordHistoryService.rememberPassword("older-password!")
    passwordHistoryService.rememberPassword("hunter2!")
    window.rebuildPasswordMenu()

    olderEntry = [a for a in window.passwordMenu.actions() if a.text() == "o...!"][0]
    olderEntry.trigger()

    assert window.activePassword == "older-password!"
    assert window.passwordLabel.text() == "Password: o...!"


def testLastPasswordUsedEntrySelectsMostRecent(window) -> None:
    passwordHistoryService.rememberPassword("older-password!")
    passwordHistoryService.rememberPassword("hunter2!")
    window.rebuildPasswordMenu()

    window.passwordMenu.actions()[0].trigger()

    assert window.activePassword == "hunter2!"


def testNewPasswordDialogSelectsPassword(window, monkeypatch) -> None:
    monkeypatch.setattr(PasswordDialog, "getPassword", staticmethod(lambda parent=None: "fresh-pw"))

    window.onNewPassword()

    assert window.activePassword == "fresh-pw"
    assert window.passwordLabel.text() == "Password: f...w"


def testClearPasswordHistory(window) -> None:
    passwordHistoryService.rememberPassword("hunter2!")
    window.usePassword("hunter2!")

    window.onClearPasswordHistory()

    assert passwordHistoryService.loadPasswords() == []
    assert window.activePassword is None
    assert window.passwordLabel.text() == "No password selected"


def testCloakShowsResultAndCopiesIt(window, qtbot) -> None:
    window.inputEdit.setPlainText("my secret note")
    window.usePassword("hunter2!")

    qtbot.mouseClick(window.cloakButton, Qt.MouseButton.LeftButton)

    cloaked = window.outputEdit.toPlainText()
    assert decryptText(cloaked, "hunter2!") == "my secret note"
    qtbot.waitUntil(lambda: clipboardService.readText() == cloaked, timeout=5000)
    assert "Cloaked and copied" in window.statusBar().currentMessage()


def testCloakRemembersThePassword(window, qtbot) -> None:
    window.inputEdit.setPlainText("note")
    window.usePassword("brand-new-pw!")

    qtbot.mouseClick(window.cloakButton, Qt.MouseButton.LeftButton)

    assert passwordHistoryService.loadPasswords() == ["brand-new-pw!"]


def testUncloakShowsPlainTextWithoutTouchingClipboard(window, qtbot) -> None:
    cloaked = encryptText("the original", "pw123")
    setClipboard(qtbot, cloaked)
    window.inputEdit.setPlainText(cloaked)
    window.usePassword("pw123")

    qtbot.mouseClick(window.uncloakButton, Qt.MouseButton.LeftButton)

    assert window.outputEdit.toPlainText() == "the original"
    # The whole point: the secret is on screen but never on the clipboard.
    assert clipboardService.readText() == cloaked
    assert "click Copy" in window.statusBar().currentMessage()


def testWrongPasswordShowsErrorAndIsNotRemembered(window, qtbot) -> None:
    window.inputEdit.setPlainText(encryptText("the original", "right password"))
    window.usePassword("wrong password")

    qtbot.mouseClick(window.uncloakButton, Qt.MouseButton.LeftButton)

    assert window.outputEdit.toPlainText() == ""
    assert "Wrong password" in window.statusBar().currentMessage()
    assert passwordHistoryService.loadPasswords() == []


def testCloakWithoutPasswordPromptsDialog(window, qtbot, monkeypatch) -> None:
    monkeypatch.setattr(PasswordDialog, "getPassword", staticmethod(lambda parent=None: "typed-pw"))
    window.inputEdit.setPlainText("something")

    qtbot.mouseClick(window.cloakButton, Qt.MouseButton.LeftButton)

    assert decryptText(window.outputEdit.toPlainText(), "typed-pw") == "something"


def testCloakWithCancelledDialogShowsHint(window, qtbot, monkeypatch) -> None:
    monkeypatch.setattr(PasswordDialog, "getPassword", staticmethod(lambda parent=None: None))
    window.inputEdit.setPlainText("something")

    qtbot.mouseClick(window.cloakButton, Qt.MouseButton.LeftButton)

    assert window.outputEdit.toPlainText() == ""
    assert "Enter a password first" in window.statusBar().currentMessage()


def testCloakWithEmptyInputShowsHint(window, qtbot) -> None:
    window.inputEdit.setPlainText("")
    window.usePassword("pw")

    qtbot.mouseClick(window.cloakButton, Qt.MouseButton.LeftButton)

    assert "Nothing to cloak" in window.statusBar().currentMessage()


def testCopyPutsUncloakedResultOnClipboard(window, qtbot) -> None:
    window.inputEdit.setPlainText(encryptText("copy me", "pw"))
    window.usePassword("pw")
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
    window.usePassword("pw")
    qtbot.mouseClick(window.uncloakButton, Qt.MouseButton.LeftButton)
    qtbot.mouseClick(window.copyButton, Qt.MouseButton.LeftButton)
    qtbot.waitUntil(lambda: clipboardService.readText() == "sensitive", timeout=5000)

    window.close()

    assert clipboardService.readText() == ""


def testClosingKeepsCloakedTextPasteable(window, qtbot) -> None:
    window.inputEdit.setPlainText("not secret once encrypted")
    window.usePassword("pw")
    qtbot.mouseClick(window.cloakButton, Qt.MouseButton.LeftButton)
    cloaked = window.outputEdit.toPlainText()
    qtbot.waitUntil(lambda: clipboardService.readText() == cloaked, timeout=5000)

    window.close()

    assert clipboardService.readText() == cloaked


def testClosingLeavesUnrelatedClipboardAlone(window, qtbot) -> None:
    setClipboard(qtbot, "the user's own clipboard content")

    window.close()

    assert clipboardService.readText() == "the user's own clipboard content"


def testAboutTextContents(window) -> None:
    aboutText = window.buildAboutText()

    assert "CloakClip" in aboutText
    assert "Editor: Francois Charette, PhD" in aboutText
    assert "AI Agent: Claude - Fable 5" in aboutText
    assert "Charette AI Group, LLC" in aboutText
