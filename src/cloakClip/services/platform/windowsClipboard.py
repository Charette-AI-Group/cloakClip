"""Windows clipboard protections: Win+V history and secret marking.

Verified against the live Windows API: text written with the secret
formats is not recorded in clipboard history, while staying pasteable.
"""

from __future__ import annotations

import asyncio
import logging

from cloakClip.services.platform.clipboardBackend import ClipboardBackend

logger = logging.getLogger(__name__)

try:
    from winrt.windows.applicationmodel.datatransfer import Clipboard as winrtClipboard
    from winrt.windows.applicationmodel.datatransfer import StandardDataFormats
except ImportError:  # pragma: no cover - the packages ship Windows-only wheels
    winrtClipboard = None
    StandardDataFormats = None

# Registered Windows clipboard formats that clipboard history and cloud
# sync honour; a DWORD 0 means "do not record this item". Password
# managers use the same ones.
secretFormats = (
    "CanIncludeInClipboardHistory",
    "CanUploadToCloudClipboard",
    "ExcludeClipboardContentFromMonitorProcessing",
)
dwordFalse = bytes(4)


def qtMimeType(formatName: str) -> str:
    """Qt's spelling for a raw registered Windows clipboard format."""
    return f'application/x-qt-windows-mime;value="{formatName}"'


class WindowsClipboardBackend(ClipboardBackend):
    name = "windows"

    @property
    def supportsHistory(self) -> bool:
        return winrtClipboard is not None

    def secretMimeData(self) -> dict[str, bytes]:
        return {qtMimeType(formatName): dwordFalse for formatName in secretFormats}

    def isHistoryEnabled(self) -> bool:
        if winrtClipboard is None:
            return False
        return bool(winrtClipboard.is_history_enabled())

    def clearHistory(self) -> bool:
        """Purge Windows clipboard history. Items the user pinned are kept."""
        if winrtClipboard is None:
            return False
        try:
            return bool(winrtClipboard.clear_history())
        except (OSError, RuntimeError):
            logger.exception("Clearing clipboard history failed")
            return False

    async def _deleteMatchingAsync(self, texts: set[str]) -> int:
        result = await winrtClipboard.get_history_items_async()
        deleted = 0
        for item in list(result.items):
            if not item.content.contains(StandardDataFormats.text):
                continue
            text = await item.content.get_text_async()
            if text in texts and winrtClipboard.delete_item_from_history(item):
                deleted += 1
        return deleted

    def deleteHistoryTexts(self, texts: set[str]) -> int:
        """Blocking: call from a worker thread or at shutdown, not mid-GUI."""
        if winrtClipboard is None or not texts:
            return 0
        try:
            return asyncio.run(self._deleteMatchingAsync(set(texts)))
        except (OSError, RuntimeError, ValueError):
            logger.exception("Deleting clipboard history items failed")
            return 0
