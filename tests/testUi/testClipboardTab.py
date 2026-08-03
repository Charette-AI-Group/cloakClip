"""Tests for the Clipboard tab: one-click operations on the clipboard."""

from __future__ import annotations

from cloakClip.services import clipboardService, passwordHistoryService
from cloakClip.services.cryptoService import decryptText, encryptText


def testCloakReplacesClipboard(window, qtbot, setClipboard) -> None:
    window.usePassword("hunter2!")

    def cloakSucceeded() -> bool:
        setClipboard("my secret note")
        window.clipboardTab.cloakButton.click()
        try:
            return decryptText(clipboardService.readText(), "hunter2!") == "my secret note"
        except Exception:
            return False

    qtbot.waitUntil(cloakSucceeded, timeout=5000)
    assert clipboardService.readText() != "my secret note"
    assert "cloaked" in window.statusBar().currentMessage()


def testUncloakReplacesClipboardMarkedSecret(window, qtbot, setClipboard) -> None:
    cloaked = encryptText("the original", "pw123")
    window.usePassword("pw123")

    def uncloakSucceeded() -> bool:
        setClipboard(cloaked)
        window.clipboardTab.uncloakButton.click()
        return clipboardService.readText() == "the original"

    qtbot.waitUntil(uncloakSucceeded, timeout=5000)
    # Plain text goes back on the clipboard, but flagged for exit cleanup
    # and excluded from Win+V history.
    assert window.lastWriteWasSecret
    assert clipboardService.currentTextIsMarkedSecret()
    assert "kept out of clipboard history" in window.statusBar().currentMessage()


def testCloakDoesNotMarkSecret(window, qtbot, setClipboard) -> None:
    setClipboard("public once encrypted")
    window.usePassword("pw")

    window.clipboardTab.cloakButton.click()

    assert not window.lastWriteWasSecret


def testSuccessfulCloakRemembersPassword(window, qtbot, setClipboard) -> None:
    setClipboard("note")
    window.usePassword("brand-new-pw!")

    window.clipboardTab.cloakButton.click()

    assert passwordHistoryService.loadPasswords() == ["brand-new-pw!"]


def testWrongPasswordLeavesClipboardAndHistoryAlone(window, qtbot, setClipboard) -> None:
    cloaked = encryptText("the original", "right password")
    setClipboard(cloaked)
    window.usePassword("wrong password")

    window.clipboardTab.uncloakButton.click()

    assert clipboardService.readText() == cloaked
    assert "Wrong password" in window.statusBar().currentMessage()
    assert passwordHistoryService.loadPasswords() == []


def testCloakWithEmptyClipboardShowsHint(window, qtbot) -> None:
    qtbot.waitUntil(clipboardService.clearText, timeout=5000)
    window.usePassword("pw")

    window.clipboardTab.cloakButton.click()

    assert "Clipboard is empty" in window.statusBar().currentMessage()


def testEditingThePreviewUpdatesTheClipboard(window, qtbot, setClipboard) -> None:
    setClipboard("shopping list")

    window.clipboardTab.previewEdit.setPlainText("shopping list and milk")

    qtbot.waitUntil(
        lambda: clipboardService.readText() == "shopping list and milk", timeout=5000
    )


def testEditingAnUncloakedSecretStaysProtected(window, qtbot, setClipboard) -> None:
    setClipboard(encryptText("meet at six", "pw"))
    window.usePassword("pw")
    window.clipboardTab.uncloakButton.click()
    qtbot.waitUntil(lambda: clipboardService.readText() == "meet at six", timeout=5000)

    window.clipboardTab.previewEdit.setPlainText("meet at seven")

    qtbot.waitUntil(lambda: clipboardService.readText() == "meet at seven", timeout=5000)
    # The edited plain text is still a secret: marked, and tracked for the
    # exit cleanup and the re-copy guard.
    assert window.lastWriteWasSecret
    assert clipboardService.currentTextIsMarkedSecret()
    assert "meet at seven" in window.sessionSecrets


def testCloakingImmediatelyAfterAnEditUsesTheEdit(window, qtbot, setClipboard) -> None:
    # No wait between typing and clicking: the pending edit must be flushed
    # first, or the stale clipboard text would be encrypted instead.
    setClipboard("original text")
    window.usePassword("pw")

    window.clipboardTab.previewEdit.setPlainText("edited text")
    window.clipboardTab.cloakButton.click()

    cloaked = window.clipboardTab.previewEdit.toPlainText()
    assert decryptText(cloaked, "pw") == "edited text"


def testEditingPlainTextIsNotMarkedSecret(window, qtbot, setClipboard) -> None:
    setClipboard("just a note")

    window.clipboardTab.previewEdit.setPlainText("just a longer note")

    qtbot.waitUntil(
        lambda: clipboardService.readText() == "just a longer note", timeout=5000
    )
    assert not window.lastWriteWasSecret


def testCloakingShowsTheCloakedTextInThePreview(window, qtbot, setClipboard) -> None:
    setClipboard("secret note")
    window.usePassword("pw")

    window.clipboardTab.cloakButton.click()

    shown = window.clipboardTab.previewEdit.toPlainText()
    assert decryptText(shown, "pw") == "secret note"
    assert not window.clipboardTab.contentIsSecret


def testPreviewFollowsClipboard(window, qtbot, setClipboard) -> None:
    setClipboard("watch me appear")

    qtbot.waitUntil(
        lambda: window.clipboardTab.previewEdit.toPlainText() == "watch me appear",
        timeout=5000,
    )


def testClearEmptiesClipboardAndHistory(window, qtbot, historyCalls, setClipboard) -> None:
    setClipboard("leftover secret")

    def clearSucceeded() -> bool:
        window.clipboardTab.clearButton.click()
        return clipboardService.readText() == ""

    qtbot.waitUntil(clearSucceeded, timeout=5000)

    assert historyCalls, "the Clear button must purge clipboard history too"
    assert window.statusBar().currentMessage() == "Clipboard and clipboard history cleared."
