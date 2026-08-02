"""Clipboard access, with whatever secret handling the platform offers.

Reading and writing is Qt's job and works everywhere. Keeping a decrypted
secret out of the OS clipboard history is not, so that part is delegated
to a per-platform backend; on a platform without one the app still runs,
with the protections reported as unavailable rather than pretended.
"""

from __future__ import annotations

import logging
import sys

from PySide6.QtCore import QMimeData
from PySide6.QtGui import QGuiApplication

from cloakClip.services.platform.clipboardBackend import ClipboardBackend

logger = logging.getLogger(__name__)

writeAttempts = 3


def createBackend() -> ClipboardBackend:
    if sys.platform == "win32":
        from cloakClip.services.platform.windowsClipboard import WindowsClipboardBackend

        return WindowsClipboardBackend()
    # macOS and Linux: reading and writing work, protections do not yet.
    logger.info("No clipboard protection backend for platform %s", sys.platform)
    return ClipboardBackend()


backend = createBackend()


def buildMimeData(text: str, secret: bool) -> QMimeData:
    mimeData = QMimeData()
    mimeData.setText(text)
    if secret:
        for mimeType, payload in backend.secretMimeData().items():
            mimeData.setData(mimeType, payload)
    return mimeData


def currentTextIsMarkedSecret() -> bool:
    mimeData = QGuiApplication.clipboard().mimeData()
    secretTypes = backend.secretMimeData()
    if mimeData is None or not secretTypes:
        return False
    return any(mimeData.hasFormat(mimeType) for mimeType in secretTypes)


def readText() -> str:
    return QGuiApplication.clipboard().text()


def writeText(text: str, secret: bool = False) -> bool:
    """Put text on the clipboard, confirming it landed.

    The clipboard is a shared OS resource and another process can hold it
    briefly, so the write is verified and retried rather than assumed.
    """
    clipboard = QGuiApplication.clipboard()
    for _ in range(writeAttempts):
        clipboard.setMimeData(buildMimeData(text, secret))
        if clipboard.text() == text:
            return True
    logger.warning("Clipboard write failed after %d attempts", writeAttempts)
    return False


def clearText() -> bool:
    clipboard = QGuiApplication.clipboard()
    for _ in range(writeAttempts):
        clipboard.clear()
        if not clipboard.text():
            return True
    logger.warning("Clipboard clear failed after %d attempts", writeAttempts)
    return False


def supportsHistory() -> bool:
    return backend.supportsHistory


def isHistoryEnabled() -> bool:
    return backend.isHistoryEnabled()


def clearHistory() -> bool:
    return backend.clearHistory()


def deleteHistoryTexts(texts: set[str]) -> int:
    return backend.deleteHistoryTexts(texts)
