"""Clipboard access, with Windows secret handling.

Text written as a secret carries the registered Windows clipboard formats
that password managers use, so Windows keeps it out of clipboard history
(Win+V) and out of cloud sync. Cloaked text is written normally: it is
encrypted, so there is no reason to hide it from history.
"""

from __future__ import annotations

import asyncio
import logging

from PySide6.QtCore import QMimeData
from PySide6.QtGui import QGuiApplication

logger = logging.getLogger(__name__)

try:
    from winrt.windows.applicationmodel.datatransfer import Clipboard as winrtClipboard
    from winrt.windows.applicationmodel.datatransfer import StandardDataFormats
except ImportError:  # pragma: no cover - the package ships Windows-only wheels
    winrtClipboard = None
    StandardDataFormats = None
    logger.warning("winrt clipboard bindings unavailable; history cannot be cleared")

# A DWORD 0 on these registered formats means "do not record this item".
secretFormats = (
    "CanIncludeInClipboardHistory",
    "CanUploadToCloudClipboard",
    "ExcludeClipboardContentFromMonitorProcessing",
)
secretMimeTypes = tuple(
    f'application/x-qt-windows-mime;value="{formatName}"' for formatName in secretFormats
)
dwordFalse = bytes(4)
writeAttempts = 3


def buildMimeData(text: str, secret: bool) -> QMimeData:
    mimeData = QMimeData()
    mimeData.setText(text)
    if secret:
        for mimeType in secretMimeTypes:
            mimeData.setData(mimeType, dwordFalse)
    return mimeData


def currentTextIsMarkedSecret() -> bool:
    mimeData = QGuiApplication.clipboard().mimeData()
    return mimeData is not None and any(
        mimeData.hasFormat(mimeType) for mimeType in secretMimeTypes
    )


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


async def _deleteHistoryTextsAsync(texts: set[str]) -> int:
    result = await winrtClipboard.get_history_items_async()
    deleted = 0
    for item in list(result.items):
        if not item.content.contains(StandardDataFormats.text):
            continue
        text = await item.content.get_text_async()
        if text in texts and winrtClipboard.delete_item_from_history(item):
            deleted += 1
    return deleted


def deleteHistoryTexts(texts: set[str]) -> int:
    """Delete every Win+V history item whose text matches one of texts.

    Blocking (runs its own event loop) — call from a worker thread or at
    shutdown, not from the GUI thread during normal use.
    """
    if winrtClipboard is None or not texts:
        return 0
    try:
        return asyncio.run(_deleteHistoryTextsAsync(set(texts)))
    except (OSError, RuntimeError, ValueError):
        logger.exception("Deleting clipboard history items failed")
        return 0
