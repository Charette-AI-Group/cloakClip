"""Tests for the platform clipboard backends.

The generic backend is what a platform without support gets, so its
contract matters: everything must degrade quietly instead of raising.
"""

from __future__ import annotations

import sys

import pytest

from cloakClip.services import clipboardService
from cloakClip.services.platform.clipboardBackend import ClipboardBackend


def testGenericBackendDegradesQuietly() -> None:
    backend = ClipboardBackend()

    assert backend.secretMimeData() == {}
    assert not backend.supportsSecretMarking
    assert not backend.supportsHistory
    assert not backend.isHistoryEnabled()
    assert not backend.clearHistory()
    assert backend.deleteHistoryTexts({"anything"}) == 0


def testChosenBackendMatchesThePlatform() -> None:
    backend = clipboardService.backend

    if sys.platform == "win32":
        assert backend.name == "windows"
    else:
        assert backend.name == "generic"


@pytest.mark.skipif(sys.platform != "win32", reason="Windows-only protections")
def testWindowsBackendOffersTheProtections() -> None:
    backend = clipboardService.backend

    assert backend.supportsSecretMarking
    assert backend.supportsHistory
    # Three registered formats, each a DWORD 0 meaning "do not record".
    payloads = backend.secretMimeData()
    assert len(payloads) == 3
    assert all(payload == bytes(4) for payload in payloads.values())
    assert all(mimeType.startswith("application/x-qt-windows-mime") for mimeType in payloads)


def testServiceDelegatesHistoryCallsToTheBackend(monkeypatch) -> None:
    calls: list[str] = []

    class RecordingBackend(ClipboardBackend):
        name = "recording"

        def isHistoryEnabled(self) -> bool:
            calls.append("isHistoryEnabled")
            return True

        def clearHistory(self) -> bool:
            calls.append("clearHistory")
            return True

        def deleteHistoryTexts(self, texts: set[str]) -> int:
            calls.append("deleteHistoryTexts")
            return len(texts)

    monkeypatch.setattr(clipboardService, "backend", RecordingBackend())

    assert clipboardService.isHistoryEnabled()
    assert clipboardService.clearHistory()
    assert clipboardService.deleteHistoryTexts({"a", "b"}) == 2
    assert calls == ["isHistoryEnabled", "clearHistory", "deleteHistoryTexts"]
