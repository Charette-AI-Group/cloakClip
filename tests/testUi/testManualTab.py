"""Tests for the Manual tab: explicit input, result, Copy and Paste."""

from __future__ import annotations

from cloakClip.services import clipboardService
from cloakClip.services.cryptoService import decryptText, encryptText
from cloakClip.ui.dialogs.passwordDialog import PasswordDialog


def testCloakShowsResultWithoutCopying(window, qtbot, setClipboard) -> None:
    setClipboard("untouched clipboard")
    window.manualTab.inputEdit.setPlainText("my secret note")
    window.usePassword("hunter2!")

    window.manualTab.cloakButton.click()

    cloaked = window.manualTab.outputEdit.toPlainText()
    assert decryptText(cloaked, "hunter2!") == "my secret note"
    # Manual means manual: nothing is copied until Copy is clicked.
    assert clipboardService.readText() == "untouched clipboard"
    assert "click Copy" in window.statusBar().currentMessage()


def testUncloakShowsPlainTextWithoutCopying(window, qtbot, setClipboard) -> None:
    cloaked = encryptText("the original", "pw123")
    setClipboard(cloaked)
    window.manualTab.inputEdit.setPlainText(cloaked)
    window.usePassword("pw123")

    window.manualTab.uncloakButton.click()

    assert window.manualTab.outputEdit.toPlainText() == "the original"
    # The whole point: the secret is on screen but never on the clipboard.
    assert clipboardService.readText() == cloaked
    assert "click Copy" in window.statusBar().currentMessage()


def testCopyPutsCloakedResultOnClipboardPlain(window, qtbot) -> None:
    window.manualTab.inputEdit.setPlainText("note")
    window.usePassword("pw")
    window.manualTab.cloakButton.click()
    cloaked = window.manualTab.outputEdit.toPlainText()

    def copySucceeded() -> bool:
        window.manualTab.copyButton.click()
        return clipboardService.readText() == cloaked

    qtbot.waitUntil(copySucceeded, timeout=5000)
    assert not window.lastWriteWasSecret
    assert "Copied" in window.statusBar().currentMessage()


def testCopyPutsUncloakedResultOnClipboardAsSecret(window, qtbot) -> None:
    window.manualTab.inputEdit.setPlainText(encryptText("copy me", "pw"))
    window.usePassword("pw")
    window.manualTab.uncloakButton.click()

    def copySucceeded() -> bool:
        window.manualTab.copyButton.click()
        return clipboardService.readText() == "copy me"

    qtbot.waitUntil(copySucceeded, timeout=5000)
    assert window.lastWriteWasSecret
    assert "kept out of clipboard history" in window.statusBar().currentMessage()


def testCopyWithoutResultShowsHint(window) -> None:
    window.manualTab.copyButton.click()

    assert window.statusBar().currentMessage() == "There is no result to copy yet."


def testPasteLoadsClipboardIntoInput(window, qtbot, setClipboard) -> None:
    setClipboard("pasted content")
    window.manualTab.inputEdit.setPlainText("")

    window.manualTab.pasteButton.click()

    assert window.manualTab.inputEdit.toPlainText() == "pasted content"


def testInputDoesNotFollowClipboard(window, qtbot, setClipboard) -> None:
    window.manualTab.inputEdit.setPlainText("typed by hand")

    setClipboard("copied elsewhere")
    qtbot.waitUntil(
        lambda: window.clipboardTab.previewEdit.toPlainText() == "copied elsewhere",
        timeout=5000,
    )

    assert window.manualTab.inputEdit.toPlainText() == "typed by hand"


def testWrongPasswordShowsError(window) -> None:
    window.manualTab.inputEdit.setPlainText(encryptText("the original", "right password"))
    window.usePassword("wrong password")

    window.manualTab.uncloakButton.click()

    assert window.manualTab.outputEdit.toPlainText() == ""
    assert "Wrong password" in window.statusBar().currentMessage()


def testCloakWithoutPasswordPromptsDialog(window, monkeypatch) -> None:
    monkeypatch.setattr(PasswordDialog, "getPassword", staticmethod(lambda parent=None: "typed-pw"))
    window.manualTab.inputEdit.setPlainText("something")

    window.manualTab.cloakButton.click()

    assert decryptText(window.manualTab.outputEdit.toPlainText(), "typed-pw") == "something"


def testCloakWithCancelledDialogShowsHint(window, monkeypatch) -> None:
    monkeypatch.setattr(PasswordDialog, "getPassword", staticmethod(lambda parent=None: None))
    window.manualTab.inputEdit.setPlainText("something")

    window.manualTab.cloakButton.click()

    assert window.manualTab.outputEdit.toPlainText() == ""
    assert "Enter a password first" in window.statusBar().currentMessage()


def testCloakWithEmptyInputShowsHint(window) -> None:
    window.manualTab.inputEdit.setPlainText("")
    window.usePassword("pw")

    window.manualTab.cloakButton.click()

    assert "Nothing to cloak" in window.statusBar().currentMessage()
