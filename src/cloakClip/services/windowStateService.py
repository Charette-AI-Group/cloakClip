"""Remember the main window's size and position between sessions.

Stored as an INI file next to the password history rather than in the
registry, so it can be inspected or deleted like any other file.
"""

from __future__ import annotations

import logging

from PySide6.QtCore import QByteArray, QSettings

from cloakClip import appConfig

logger = logging.getLogger(__name__)

geometryKey = "mainWindow/geometry"


def openSettings() -> QSettings:
    return QSettings(str(appConfig.settingsFile), QSettings.Format.IniFormat)


def saveGeometry(geometry: QByteArray) -> None:
    appConfig.settingsFile.parent.mkdir(parents=True, exist_ok=True)
    settings = openSettings()
    settings.setValue(geometryKey, geometry)
    settings.sync()
    if settings.status() != QSettings.Status.NoError:
        logger.warning("Could not save window geometry to %s", appConfig.settingsFile)


def loadGeometry() -> QByteArray | None:
    value = openSettings().value(geometryKey)
    if isinstance(value, QByteArray) and not value.isEmpty():
        return value
    return None


def clearGeometry() -> None:
    settings = openSettings()
    settings.remove(geometryKey)
    settings.sync()
