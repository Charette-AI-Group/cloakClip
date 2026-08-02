"""Tests for the application icon resource."""

from __future__ import annotations

from PySide6.QtGui import QIcon

from cloakClip import appConfig

expectedSizes = (16, 24, 32, 48, 64, 128, 256)


def testIconFileExists() -> None:
    assert appConfig.iconFile.exists(), (
        f"{appConfig.iconFile} missing — run: python tools/makeIcon.py"
    )


def testIconLoadsWithAllSizes(qapp) -> None:
    icon = QIcon(str(appConfig.iconFile))

    assert not icon.isNull()
    available = {size.width() for size in icon.availableSizes()}
    assert set(expectedSizes) <= available, f"missing sizes: {set(expectedSizes) - available}"


def testIconRendersOpaquePixels(qapp) -> None:
    # A blank or fully transparent icon would still load; check it has paint.
    image = QIcon(str(appConfig.iconFile)).pixmap(32, 32).toImage()

    opaque = sum(
        1
        for y in range(image.height())
        for x in range(image.width())
        if image.pixelColor(x, y).alpha() > 0
    )
    assert opaque > (image.width() * image.height()) // 2
