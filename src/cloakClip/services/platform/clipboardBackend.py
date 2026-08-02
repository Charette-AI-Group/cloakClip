"""The clipboard behaviour that differs between operating systems.

Everything here is about *protecting* clipboard content, which is exactly
the part no cross-platform toolkit abstracts. Plain reading and writing is
handled by Qt in clipboardService and is not part of this interface.

The base class is a working no-op backend: on a platform without support,
the app runs with the protections quietly unavailable rather than failing.
Callers must therefore treat every result as "best effort" and check
supportsHistory before promising the user anything.
"""

from __future__ import annotations


class ClipboardBackend:
    name = "generic"

    @property
    def supportsSecretMarking(self) -> bool:
        """Whether the OS can be told to keep text out of clipboard managers."""
        return bool(self.secretMimeData())

    @property
    def supportsHistory(self) -> bool:
        """Whether the OS keeps a clipboard history this app can manage."""
        return False

    def secretMimeData(self) -> dict[str, bytes]:
        """Extra mime entries that mark clipboard text as secret.

        Returned as mime type -> payload so the caller can attach them to a
        QMimeData without knowing what they mean.
        """
        return {}

    def isHistoryEnabled(self) -> bool:
        """Whether the user currently has clipboard history switched on."""
        return False

    def clearHistory(self) -> bool:
        """Purge the whole clipboard history. True if it happened."""
        return False

    def deleteHistoryTexts(self, texts: set[str]) -> int:
        """Delete history entries matching texts. Returns how many went."""
        return 0
