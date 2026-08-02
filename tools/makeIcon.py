"""Generate the CloakClip application icon.

Draws the artwork with QPainter at each icon size (so small sizes stay
crisp instead of being mushy downscales) and packs the PNGs into a
multi-resolution .ico. Run it after changing the design:

    .venv\\Scripts\\python.exe tools\\makeIcon.py
"""

from __future__ import annotations

import struct
import sys
from pathlib import Path

from PySide6.QtCore import QBuffer, QByteArray, QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QPixmap
from PySide6.QtWidgets import QApplication

projectRoot = Path(__file__).resolve().parents[1]
outputFile = projectRoot / "src" / "cloakClip" / "resources" / "cloakClip.ico"
previewFile = projectRoot / "src" / "cloakClip" / "resources" / "cloakClip.png"

iconSizes = (16, 24, 32, 48, 64, 128, 256)

backgroundTop = QColor("#4F46E5")
backgroundBottom = QColor("#9333EA")
boardColor = QColor("#FFFFFF")
clipColor = QColor("#C7D2FE")
plainLineColor = QColor("#4F46E5")
cipherBlockColor = QColor("#A5B4FC")


def drawIcon(size: int) -> QPixmap:
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(Qt.PenStyle.NoPen)

    # Small icons need proportionally tighter corners and a roomier board,
    # or the artwork collapses into an unreadable white blob.
    small = size < 32
    cornerRadius = size * (0.18 if small else 0.22)

    # Rounded-square background with the app's indigo/violet gradient.
    gradient = QLinearGradient(QPointF(0, 0), QPointF(0, size))
    gradient.setColorAt(0.0, backgroundTop)
    gradient.setColorAt(1.0, backgroundBottom)
    painter.setBrush(gradient)
    painter.drawRoundedRect(QRectF(0, 0, size, size), cornerRadius, cornerRadius)

    # Clipboard body.
    boardWidth = size * (0.58 if small else 0.52)
    boardHeight = size * (0.56 if small else 0.60)
    boardX, boardY = (size - boardWidth) / 2, size * (0.30 if small else 0.26)
    painter.setBrush(boardColor)
    painter.drawRoundedRect(
        QRectF(boardX, boardY, boardWidth, boardHeight), size * 0.07, size * 0.07
    )

    # The clip at the top. It overlaps the white board, so a pale fill would
    # merge with it at small sizes — use the deep indigo there instead.
    clipWidth = size * (0.30 if small else 0.26)
    clipHeight = size * (0.14 if small else 0.13)
    painter.setBrush(plainLineColor if small else clipColor)
    painter.drawRoundedRect(
        QRectF((size - clipWidth) / 2, size * (0.20 if small else 0.17), clipWidth, clipHeight),
        size * 0.045,
        size * 0.045,
    )

    drawContentLines(painter, size, boardX, boardY, boardWidth, boardHeight)

    painter.end()
    return pixmap


def drawContentLines(
    painter: QPainter,
    size: int,
    boardX: float,
    boardY: float,
    boardWidth: float,
    boardHeight: float,
) -> None:
    """Solid lines (plain text) dissolving into blocks (encrypted).

    Small sizes get fewer, chunkier rows: at 16px a four-block row is a grey
    smear, while two bold rows still say "document that turns into cipher".
    """
    small = size < 32
    marginX = boardWidth * (0.14 if small else 0.16)
    lineX = boardX + marginX
    lineWidth = boardWidth - marginX * 2
    lineHeight = boardHeight * (0.11 if small else 0.075)
    radius = lineHeight / 2
    top = boardY + boardHeight * (0.26 if small else 0.22)
    step = boardHeight * (0.26 if small else 0.165)

    plainRows = 1 if small else 2
    painter.setBrush(plainLineColor)
    for index in range(plainRows):
        width = lineWidth if index == 0 else lineWidth * 0.72
        painter.drawRoundedRect(
            QRectF(lineX, top + step * index, width, lineHeight), radius, radius
        )

    painter.setBrush(cipherBlockColor)
    blockGap = lineWidth * (0.10 if small else 0.07)
    blockRows = (2,) if small else (4, 3)
    for row, blocks in enumerate(blockRows):
        blockWidth = (lineWidth - blockGap * (blocks - 1)) / blocks
        rowY = top + step * (plainRows + row)
        for column in range(blocks):
            painter.drawRoundedRect(
                QRectF(
                    lineX + (blockWidth + blockGap) * column, rowY, blockWidth, lineHeight
                ),
                radius,
                radius,
            )


def pngBytes(pixmap: QPixmap) -> bytes:
    # The QByteArray must outlive the QBuffer that writes into it.
    byteArray = QByteArray()
    buffer = QBuffer(byteArray)
    buffer.open(QBuffer.OpenModeFlag.WriteOnly)
    pixmap.save(buffer, "PNG")
    buffer.close()
    return bytes(byteArray)


def packIco(images: list[tuple[int, bytes]]) -> bytes:
    """Build an .ico holding PNG-compressed images (Windows Vista+)."""
    header = struct.pack("<HHH", 0, 1, len(images))
    entrySize = 16
    offset = len(header) + entrySize * len(images)

    entries, payloads = [], []
    for size, data in images:
        # 0 in the size byte means 256 in the ICO format.
        dimension = 0 if size >= 256 else size
        entries.append(
            struct.pack(
                "<BBBBHHII", dimension, dimension, 0, 0, 1, 32, len(data), offset
            )
        )
        payloads.append(data)
        offset += len(data)

    return header + b"".join(entries) + b"".join(payloads)


def main() -> int:
    app = QApplication(sys.argv)  # noqa: F841 - QPixmap needs an application

    outputFile.parent.mkdir(parents=True, exist_ok=True)
    images = [(size, pngBytes(drawIcon(size))) for size in iconSizes]
    outputFile.write_bytes(packIco(images))
    drawIcon(256).save(str(previewFile), "PNG")

    sizeList = ", ".join(str(size) for size in iconSizes)
    print(f"Wrote {outputFile.relative_to(projectRoot)} ({sizeList} px)")
    print(f"Wrote {previewFile.relative_to(projectRoot)} (256 px preview)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
