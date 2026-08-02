"""Remember the main window's size and position between sessions.

Stored in the app's INI file rather than the registry, so it can be
inspected or deleted like any other file.
"""

from __future__ import annotations

import logging

from PySide6.QtCore import QByteArray, QSettings

from cloakClip.services import settingsService

logger = logging.getLogger(__name__)

geometryKey = "mainWindow/geometry"


def saveGeometry(geometry: QByteArray) -> None:
    settingsService.writeValue(geometryKey, geometry)
    if settingsService.openSettings().status() != QSettings.Status.NoError:
        logger.warning("Could not save the window geometry")


def loadGeometry() -> QByteArray | None:
    value = settingsService.openSettings().value(geometryKey)
    if isinstance(value, QByteArray) and not value.isEmpty():
        return value
    return None


def clearGeometry() -> None:
    settings = settingsService.openSettings()
    settings.remove(geometryKey)
    settings.sync()
