"""Tests for the Manual tab: live sync between plain and cloaked fields."""

from __future__ import annotations

from cloakClip.services import clipboardService, passwordHistoryService
from cloakClip.services.cryptoService import decryptText, encryptText
from cloakClip.ui.dialogs.passwordDialog import PasswordDialog
from platformSkips import needsPasswordStore


def cloakFieldDecryptsTo(window, expected: str, password: str) -> bool:
    try:
        return decryptText(window.manualTab.cloakEdit.toPlainText(), password) == expected
    except Exception:
        return False


def testTypingPlainTextCloaksLive(window, qtbot) -> None:
    window.usePassword("hunter2!")

    window.manualTab.plainEdit.setPlainText("my secret note")

    qtbot.waitUntil(lambda: cloakFieldDecryptsTo(window, "my secret note", "hunter2!"),
                    timeout=5000)


def testCloakingRegistersThePlainTextAsASessionSecret(window, qtbot) -> None:
    window.usePassword("pw")

    window.manualTab.plainEdit.setPlainText("pasted from somewhere else")

    qtbot.waitUntil(
        lambda: "pasted from somewhere else" in window.sessionSecrets, timeout=5000
    )


def testEditingPlainTextRecloaks(window, qtbot) -> None:
    window.usePassword("hunter2!")
    window.manualTab.plainEdit.setPlainText("first version")
    qtbot.waitUntil(lambda: cloakFieldDecryptsTo(window, "first version", "hunter2!"),
                    timeout=5000)
    firstCloak = window.manualTab.cloakEdit.toPlainText()

    window.manualTab.plainEdit.setPlainText("second version")

    qtbot.waitUntil(lambda: cloakFieldDecryptsTo(window, "second version", "hunter2!"),
                    timeout=5000)
    assert window.manualTab.cloakEdit.toPlainText() != firstCloak


def testPastingCloakedTextUncloaksLive(window, qtbot) -> None:
    cloaked = encryptText("the original", "pw123")
    window.usePassword("pw123")

    window.manualTab.cloakEdit.setPlainText(cloaked)

    qtbot.waitUntil(
        lambda: window.manualTab.plainEdit.toPlainText() == "the original", timeout=5000
    )
    # The pasted string is left exactly as pasted, not re-encrypted.
    assert window.manualTab.cloakEdit.toPlainText() == cloaked
    assert "the original" in window.sessionSecrets


def testUncloakingDoesNotTouchClipboard(window, qtbot, setClipboard) -> None:
    cloaked = encryptText("screen only", "pw")
    setClipboard(cloaked)
    window.usePassword("pw")

    window.manualTab.cloakEdit.setPlainText(cloaked)

    qtbot.waitUntil(
        lambda: window.manualTab.plainEdit.toPlainText() == "screen only", timeout=5000
    )
    assert clipboardService.readText() == cloaked


def testWrongPasswordShowsHintAndClearsPlain(window, qtbot) -> None:
    window.usePassword("wrong password")
    window.manualTab.plainEdit.setPlainText("stale")

    window.manualTab.cloakEdit.setPlainText(encryptText("the original", "right password"))

    qtbot.waitUntil(
        lambda: "not the right password" in window.statusBar().currentMessage(),
        timeout=5000,
    )
    assert window.manualTab.plainEdit.toPlainText() == ""
    # A password that never decrypted anything is not remembered.
    assert "wrong password" not in passwordHistoryService.loadPasswords()


@needsPasswordStore
def testSuccessfulUncloakRemembersPassword(window, qtbot) -> None:
    window.usePassword("good-pw!")

    window.manualTab.cloakEdit.setPlainText(encryptText("hello", "good-pw!"))

    qtbot.waitUntil(
        lambda: window.manualTab.plainEdit.toPlainText() == "hello", timeout=5000
    )
    assert passwordHistoryService.loadPasswords() == ["good-pw!"]


def testTypingWithoutPasswordPromptsDialog(window, qtbot, monkeypatch) -> None:
    monkeypatch.setattr(
        PasswordDialog, "getPassword", staticmethod(lambda parent=None: "dialog-pw")
    )

    window.manualTab.plainEdit.setPlainText("typed before choosing a password")

    qtbot.waitUntil(
        lambda: cloakFieldDecryptsTo(window, "typed before choosing a password", "dialog-pw"),
        timeout=5000,
    )
    assert window.activePassword == "dialog-pw"


def testPastingCloakedWithoutPasswordPromptsDialog(window, qtbot, monkeypatch) -> None:
    monkeypatch.setattr(
        PasswordDialog, "getPassword", staticmethod(lambda parent=None: "dialog-pw")
    )

    window.manualTab.cloakEdit.setPlainText(encryptText("hidden message", "dialog-pw"))

    qtbot.waitUntil(
        lambda: window.manualTab.plainEdit.toPlainText() == "hidden message", timeout=5000
    )


def testDismissingDialogHintsAndDoesNotNag(window, qtbot, monkeypatch) -> None:
    prompts: list[int] = []

    def declinedDialog(parent=None) -> None:
        prompts.append(1)
        return None

    monkeypatch.setattr(PasswordDialog, "getPassword", staticmethod(declinedDialog))

    window.manualTab.plainEdit.setPlainText("first attempt")
    qtbot.waitUntil(
        lambda: "Select a password" in window.statusBar().currentMessage(), timeout=5000
    )
    assert window.manualTab.cloakEdit.toPlainText() == ""

    # Continuing to type must not reopen the dialog over and over.
    window.manualTab.plainEdit.setPlainText("still typing away")
    qtbot.wait(600)

    assert len(prompts) == 1

    # Choosing a password from the menu resumes the sync.
    window.usePassword("late-pw")
    qtbot.waitUntil(
        lambda: cloakFieldDecryptsTo(window, "still typing away", "late-pw"), timeout=5000
    )


def testClearingPlainClearsCloak(window, qtbot) -> None:
    window.usePassword("pw")
    window.manualTab.plainEdit.setPlainText("something")
    qtbot.waitUntil(lambda: window.manualTab.cloakEdit.toPlainText() != "", timeout=5000)

    window.manualTab.plainEdit.setPlainText("")

    qtbot.waitUntil(lambda: window.manualTab.cloakEdit.toPlainText() == "", timeout=5000)


def testCloakCopyButton(window, qtbot) -> None:
    window.usePassword("pw")
    window.manualTab.plainEdit.setPlainText("note")
    qtbot.waitUntil(lambda: window.manualTab.cloakEdit.toPlainText() != "", timeout=5000)
    cloaked = window.manualTab.cloakEdit.toPlainText()

    def copySucceeded() -> bool:
        window.manualTab.cloakCopyButton.click()
        return clipboardService.readText() == cloaked

    qtbot.waitUntil(copySucceeded, timeout=5000)
    assert not window.lastWriteWasSecret


def testPlainCopyButtonIsSecretMarked(window, qtbot) -> None:
    window.usePassword("pw")
    window.manualTab.cloakEdit.setPlainText(encryptText("copy me", "pw"))
    qtbot.waitUntil(
        lambda: window.manualTab.plainEdit.toPlainText() == "copy me", timeout=5000
    )

    def copySucceeded() -> bool:
        window.manualTab.plainCopyButton.click()
        return clipboardService.readText() == "copy me"

    qtbot.waitUntil(copySucceeded, timeout=5000)
    assert window.lastWriteWasSecret
    assert "kept out of clipboard history" in window.statusBar().currentMessage()


def testCopyWithEmptyFieldsShowsHints(window) -> None:
    window.manualTab.plainCopyButton.click()
    assert window.statusBar().currentMessage() == "There is no plain text to copy."

    window.manualTab.cloakCopyButton.click()
    assert window.statusBar().currentMessage() == "There is no cloaked text to copy."


def testPlainPasteButton(window, qtbot, setClipboard) -> None:
    setClipboard("pasted plain text")
    window.usePassword("pw")

    window.manualTab.plainPasteButton.click()

    assert window.manualTab.plainEdit.toPlainText() == "pasted plain text"
    qtbot.waitUntil(
        lambda: cloakFieldDecryptsTo(window, "pasted plain text", "pw"), timeout=5000
    )


def testCloakPasteButton(window, qtbot, setClipboard) -> None:
    cloaked = encryptText("pasted secret", "pw")
    setClipboard(cloaked)
    window.usePassword("pw")

    window.manualTab.cloakPasteButton.click()

    assert window.manualTab.cloakEdit.toPlainText() == cloaked
    qtbot.waitUntil(
        lambda: window.manualTab.plainEdit.toPlainText() == "pasted secret", timeout=5000
    )


def testClearFieldsEmptiesBoth(window, qtbot) -> None:
    window.usePassword("pw")
    window.manualTab.plainEdit.setPlainText("something")
    qtbot.waitUntil(lambda: window.manualTab.cloakEdit.toPlainText() != "", timeout=5000)

    window.manualTab.clearFields()

    assert window.manualTab.plainEdit.toPlainText() == ""
    assert window.manualTab.cloakEdit.toPlainText() == ""
