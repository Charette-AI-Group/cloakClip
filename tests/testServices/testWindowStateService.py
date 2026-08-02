"""Tests for remembered window geometry."""

from __future__ import annotations

import pytest
from PySide6.QtWidgets import QWidget

from cloakClip import appConfig
from cloakClip.services import windowStateService


@pytest.fixture(autouse=True)
def isolatedSettings(tmp_path, monkeypatch):
    monkeypatch.setattr(appConfig, "settingsFile", tmp_path / "settings.ini")


def testLoadWithoutSettingsIsNone(qapp) -> None:
    assert windowStateService.loadGeometry() is None


def testSaveAndLoadRoundTrip(qapp, qtbot) -> None:
    widget = QWidget()
    qtbot.addWidget(widget)
    widget.resize(640, 480)
    saved = widget.saveGeometry()

    windowStateService.saveGeometry(saved)

    assert appConfig.settingsFile.exists()
    loaded = windowStateService.loadGeometry()
    assert loaded is not None
    assert loaded == saved


def testRestoringAppliesSavedSize(qapp, qtbot) -> None:
    source = QWidget()
    qtbot.addWidget(source)
    source.resize(517, 393)
    windowStateService.saveGeometry(source.saveGeometry())

    target = QWidget()
    qtbot.addWidget(target)
    assert target.restoreGeometry(windowStateService.loadGeometry())

    assert target.size() == source.size()


def testClearGeometry(qapp, qtbot) -> None:
    widget = QWidget()
    qtbot.addWidget(widget)
    windowStateService.saveGeometry(widget.saveGeometry())

    windowStateService.clearGeometry()

    assert windowStateService.loadGeometry() is None
