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
