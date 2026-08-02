"""Tests for the light/dark theme override."""

from __future__ import annotations

import pytest
from PySide6.QtCore import Qt

from cloakClip import appConfig
from cloakClip.services import themeService


@pytest.fixture(autouse=True)
def isolatedSettings(tmp_path, monkeypatch):
    monkeypatch.setattr(appConfig, "settingsFile", tmp_path / "settings.ini")


@pytest.fixture(autouse=True)
def restoreColorScheme(qapp):
    yield
    qapp.styleHints().unsetColorScheme()


def testDefaultIsFollowTheSystem(qapp) -> None:
    assert themeService.loadTheme() == themeService.systemTheme


def testSaveAndLoadRoundTrip(qapp) -> None:
    themeService.saveTheme(themeService.darkTheme)

    assert themeService.loadTheme() == themeService.darkTheme


def testUnknownStoredValueFallsBackToSystem(qapp) -> None:
    themeService.saveTheme("chartreuse")

    assert themeService.loadTheme() == themeService.systemTheme


def testApplyLightAndDarkChangeThePalette(qapp) -> None:
    themeService.applyTheme(themeService.lightTheme)
    assert themeService.currentColorScheme() == Qt.ColorScheme.Light
    lightWindow = qapp.palette().color(qapp.palette().ColorRole.Window)

    themeService.applyTheme(themeService.darkTheme)
    assert themeService.currentColorScheme() == Qt.ColorScheme.Dark
    darkWindow = qapp.palette().color(qapp.palette().ColorRole.Window)

    assert lightWindow != darkWindow
    assert lightWindow.lightness() > darkWindow.lightness()


def testApplySystemReleasesTheOverride(qapp) -> None:
    themeService.applyTheme(themeService.lightTheme)
    forced = themeService.currentColorScheme()

    themeService.applyTheme(themeService.systemTheme)

    # Back to whatever Windows says, which is what the app started with.
    assert themeService.currentColorScheme() == qapp.styleHints().colorScheme()
    assert isinstance(forced, Qt.ColorScheme)
