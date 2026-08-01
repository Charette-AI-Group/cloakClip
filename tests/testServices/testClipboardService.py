"""Tests for clipboard access and Windows secret handling.

These never call clipboardService.clearHistory(): it would wipe the real
Win+V history of whoever runs the suite.
"""

from __future__ import annotations

from cloakClip.services import clipboardService

secretMimeTypes = [
    f'application/x-qt-windows-mime;value="{formatName}"'
    for formatName in clipboardService.secretFormats
]


def writeWithRetry(qtbot, text: str, secret: bool = False) -> None:
    # The shared OS clipboard can be held by another process; keep trying.
    qtbot.waitUntil(lambda: clipboardService.writeText(text, secret=secret), timeout=5000)


def testNormalMimeDataCarriesOnlyText(qapp) -> None:
    mimeData = clipboardService.buildMimeData("hello", secret=False)

    assert mimeData.text() == "hello"
    for mimeType in secretMimeTypes:
        assert not mimeData.hasFormat(mimeType)


def testSecretMimeDataCarriesExclusionFormats(qapp) -> None:
    mimeData = clipboardService.buildMimeData("hello", secret=True)

    assert mimeData.text() == "hello"
    for mimeType in secretMimeTypes:
        assert mimeData.data(mimeType) == clipboardService.dwordFalse


def testWriteAndReadBack(qapp, qtbot) -> None:
    writeWithRetry(qtbot, "round trip text")
    assert clipboardService.readText() == "round trip text"


def testSecretWriteIsStillReadableByOtherApps(qapp, qtbot) -> None:
    # Excluding text from history must not make it unpasteable.
    writeWithRetry(qtbot, "secret text", secret=True)
    assert clipboardService.readText() == "secret text"


def testClearTextEmptiesClipboard(qapp, qtbot) -> None:
    writeWithRetry(qtbot, "to be cleared")
    qtbot.waitUntil(clipboardService.clearText, timeout=5000)

    assert clipboardService.readText() == ""


def testHistoryEnabledIsBoolean(qapp) -> None:
    assert isinstance(clipboardService.isHistoryEnabled(), bool)


def testCurrentTextMarkedSecretDetection(qapp, qtbot) -> None:
    writeWithRetry(qtbot, "plain write")
    assert not clipboardService.currentTextIsMarkedSecret()

    writeWithRetry(qtbot, "secret write", secret=True)
    assert clipboardService.currentTextIsMarkedSecret()


def testDeleteHistoryTextsWithNothingToDelete(qapp) -> None:
    # Empty input returns without touching the real Win+V history.
    assert clipboardService.deleteHistoryTexts(set()) == 0
