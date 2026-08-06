"""Tab widget whose tabs share the full width equally, labels centered."""

from __future__ import annotations

from PySide6.QtCore import QSize
from PySide6.QtGui import QResizeEvent
from PySide6.QtWidgets import QTabBar, QTabWidget, QWidget


class FullWidthTabBar(QTabBar):
    def tabSizeHint(self, index: int) -> QSize:
        size = super().tabSizeHint(index)
        tabWidget = self.parentWidget()
        if self.count() and tabWidget is not None:
            size.setWidth(tabWidget.width() // self.count())
        return size

    def minimumTabSizeHint(self, index: int) -> QSize:
        # The stretched tabSizeHint above is derived from the parent's current
        # width, so letting it drive the *minimum* too makes the window's
        # minimum width track its actual width. On any style that adds frame
        # padding — macOS adds 6px, Windows adds none — the minimum then always
        # lands just above the current width and the window grows without
        # bound. Keeping the minimum at the natural label width breaks that
        # loop; the tabs still stretch, since only sizeHint governs that.
        return super().tabSizeHint(index)


class FullWidthTabWidget(QTabWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setTabBar(FullWidthTabBar(self))

    def resizeEvent(self, event: QResizeEvent) -> None:
        # Tab widths derive from the widget width, so a resize must make the
        # tab bar re-query its size hints. QTabBar has no public relayout;
        # re-setting the icon size is the standard way to force one.
        super().resizeEvent(event)
        tabBar = self.tabBar()
        tabBar.setIconSize(tabBar.iconSize())
