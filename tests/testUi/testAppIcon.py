"""Tests for the application icon resources.

Each asset is checked by name rather than through appConfig.iconFile, which
resolves to only one of them per platform. Both ship in the repo, so naming
them directly means the Windows icon is still verified by a macOS run and
the macOS icon by the Windows CI job — neither covered the other before.
"""

from __future__ import annotations

from PySide6.QtGui import QIcon

from cloakClip import appConfig

# Matches iconSizes in tools/makeIcon.py.
expectedSizes = (16, 24, 32, 48, 64, 128, 256)
previewSize = 256

icoFile = appConfig.resourcesDir / "cloakClip.ico"
pngFile = appConfig.resourcesDir / "cloakClip.png"


def testIconFileExists() -> None:
    assert appConfig.iconFile.exists(), (
        f"{appConfig.iconFile} missing — run: python tools/makeIcon.py"
    )


def testIcoHoldsEveryIconSize(qapp) -> None:
    """Windows picks a size per context, so a dropped one is drawn blurry."""
    icon = QIcon(str(icoFile))

    assert not icon.isNull()
    available = {size.width() for size in icon.availableSizes()}
    assert set(expectedSizes) <= available, f"missing sizes: {set(expectedSizes) - available}"


def testPngIsTheFullSizePreview(qapp) -> None:
    """A PNG holds a single image, which is why it is not checked for sizes.

    macOS uses this file rather than the .ico, and the build converts it to
    the .icns for the app bundle — so every size in that bundle is downscaled
    from here, and shrinking it would quietly blur the whole set.
    """
    icon = QIcon(str(pngFile))

    assert not icon.isNull()
    assert {size.width() for size in icon.availableSizes()} == {previewSize}


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
