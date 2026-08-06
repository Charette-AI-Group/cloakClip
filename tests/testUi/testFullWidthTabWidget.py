"""Tests for the tab bar that stretches its tabs across the full width.

The regression these guard against is subtle. `tabSizeHint` derives a tab's
width from the parent's current width, and Qt's default `minimumTabSizeHint`
is implemented by calling that same virtual method — so the stretched width
silently became the *minimum* width too. That made the tab widget's minimum
track its actual width, and on any style whose frame adds padding (macOS adds
6px, Windows adds none) the minimum landed just above the current width on
every layout pass, growing the window without bound until it ran off-screen.

The bug is invisible to a headless run, since the offscreen platform adds no
padding, so these tests assert the underlying invariant rather than the window
size: the minimum must not depend on the width. That holds on every platform.
"""

from __future__ import annotations

import pytest
from PySide6.QtWidgets import QWidget

from cloakClip.ui.widgets.fullWidthTabWidget import FullWidthTabWidget

narrowWidth = 620
wideWidth = 1800


@pytest.fixture
def tabWidget(qtbot) -> FullWidthTabWidget:
    widget = FullWidthTabWidget()
    qtbot.addWidget(widget)
    widget.addTab(QWidget(), "Clipboard")
    widget.addTab(QWidget(), "Manual")
    widget.resize(narrowWidth, 400)
    widget.show()
    return widget


def testTabsShareTheFullWidth(tabWidget) -> None:
    tabWidget.resize(wideWidth, 400)

    hints = [tabWidget.tabBar().tabSizeHint(index).width() for index in range(2)]
    assert hints == [wideWidth // 2, wideWidth // 2]


def testMinimumTabSizeIsIndependentOfTheWidth(tabWidget) -> None:
    """The runaway-width regression: a minimum that follows the width."""
    tabBar = tabWidget.tabBar()
    narrow = [tabBar.minimumTabSizeHint(index).width() for index in range(2)]

    tabWidget.resize(wideWidth, 400)
    wide = [tabBar.minimumTabSizeHint(index).width() for index in range(2)]

    assert wide == narrow, (
        "minimumTabSizeHint grew with the widget width — the window's minimum "
        "will chase its own width and grow without bound on a padded style"
    )


def testMinimumWidthLeavesRoomToShrink(tabWidget) -> None:
    """A minimum at or above the current width is what starts the growth."""
    tabWidget.resize(wideWidth, 400)

    assert tabWidget.minimumSizeHint().width() < wideWidth
