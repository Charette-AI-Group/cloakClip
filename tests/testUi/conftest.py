"""Shared fixtures for UI tests.

clearHistory is always monkeypatched: the real call would wipe the Win+V
history of whoever runs the suite. The password history file is redirected
to a temp folder so tests never touch the real one.
"""

from __future__ import annotations

import pytest

from cloakClip import appConfig
from cloakClip.services import clipboardService
from cloakClip.ui.dialogs.passwordDialog import PasswordDialog
from cloakClip.ui.mainWindow import MainWindow


@pytest.fixture
def setClipboard(qtbot):
    def setter(text: str) -> None:
        # The shared OS clipboard can be held by another process; keep trying.
        qtbot.waitUntil(lambda: clipboardService.writeText(text), timeout=5000)

    return setter


@pytest.fixture(autouse=True)
def isolatedPasswordHistory(tmp_path, monkeypatch):
    monkeypatch.setattr(appConfig, "passwordHistoryFile", tmp_path / "passwordHistory.bin")


@pytest.fixture(autouse=True)
def noRealPasswordDialog(monkeypatch):
    """Never open a real modal dialog — it would block the suite forever.

    Declining is the default; tests that want a password supplied override
    getPassword themselves.
    """
    monkeypatch.setattr(
        PasswordDialog, "getPassword", staticmethod(lambda parent=None: None)
    )


@pytest.fixture(autouse=True)
def purgeCalls(monkeypatch) -> list[set[str]]:
    calls: list[set[str]] = []

    def fakeDeleteHistoryTexts(texts: set[str]) -> int:
        calls.append(set(texts))
        return len(texts)

    monkeypatch.setattr(clipboardService, "deleteHistoryTexts", fakeDeleteHistoryTexts)
    return calls


@pytest.fixture
def historyCalls(monkeypatch) -> list[bool]:
    calls: list[bool] = []

    def fakeClearHistory() -> bool:
        calls.append(True)
        return True

    monkeypatch.setattr(clipboardService, "clearHistory", fakeClearHistory)
    return calls


@pytest.fixture
def window(qtbot, historyCalls) -> MainWindow:
    mainWindow = MainWindow()
    qtbot.addWidget(mainWindow)
    mainWindow.show()
    return mainWindow
