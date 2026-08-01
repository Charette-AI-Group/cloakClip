"""Clipboard access, with Windows secret handling.

Text written as a secret carries the registered Windows clipboard formats
that password managers use, so Windows keeps it out of clipboard history
(Win+V) and out of cloud sync. Cloaked text is written normally: it is
encrypted, so there is no reason to hide it from history.
"""

from __future__ import annotations

import logging

from PySide6.QtCore import QMimeData
from PySide6.QtGui import QGuiApplication

logger = logging.getLogger(__name__)

try:
    from winrt.windows.applicationmodel.datatransfer import Clipboard as winrtClipboard
except ImportError:  # pragma: no cover - the package ships Windows-only wheels
    winrtClipboard = None
    logger.warning("winrt clipboard bindings unavailable; history cannot be cleared")

# A DWORD 0 on these registered formats means "do not record this item".
secretFormats = (
    "CanIncludeInClipboardHistory",
    "CanUploadToCloudClipboard",
    "ExcludeClipboardContentFromMonitorProcessing",
)
dwordFalse = bytes(4)
writeAttempts = 3


def buildMimeData(text: str, secret: bool) -> QMimeData:
    mimeData = QMimeData()
    mimeData.setText(text)
    if secret:
        for formatName in secretFormats:
            mimeData.setData(
                f'application/x-qt-windows-mime;value="{formatName}"', dwordFalse
            )
    return mimeData


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


def isHistoryEnabled() -> bool:
    if winrtClipboard is None:
        return False
    return bool(winrtClipboard.is_history_enabled())


def clearHistory() -> bool:
    """Purge Windows clipboard history. Items the user pinned are kept."""
    if winrtClipboard is None:
        return False
    try:
        return bool(winrtClipboard.clear_history())
    except (OSError, RuntimeError):
        logger.exception("Clearing clipboard history failed")
        return False
