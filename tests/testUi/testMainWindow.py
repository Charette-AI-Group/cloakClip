"""Tests for the main window: tabs, menus, passwords, exit behavior."""

from __future__ import annotations

import pytest
from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QGuiApplication

from cloakClip import appConfig
from cloakClip.services import clipboardService, passwordHistoryService, themeService
from cloakClip.services.cryptoService import encryptText
from cloakClip.ui.dialogs.passwordDialog import PasswordDialog
from cloakClip.ui.mainWindow import MainWindow


def testMainWindowOpens(window) -> None:
    assert window.isVisible()
    assert window.windowTitle() == "CloakClip"
    assert window.statusBar().currentMessage() == "Ready"
    assert window.passwordLabel.text() == "No password selected"


def testTwoTabs(window) -> None:
    tabTitles = [window.tabWidget.tabText(i) for i in range(window.tabWidget.count())]
    assert tabTitles == ["&Clipboard", "&Manual"]
    assert window.tabWidget.currentWidget() is window.clipboardTab


def testTabsEachTakeHalfTheWidth(window, qtbot) -> None:
    def halvesFill() -> bool:
        tabBar = window.tabWidget.tabBar()
        half = window.tabWidget.width() // 2
        return all(
            abs(tabBar.tabRect(i).width() - half) <= 1 for i in range(tabBar.count())
        )

    qtbot.waitUntil(halvesFill, timeout=5000)

    window.resize(window.width() + 200, window.height())
    qtbot.waitUntil(halvesFill, timeout=5000)


def testTabLabelsAreEmphasised(window) -> None:
    tabBar = window.tabWidget.tabBar()

    assert tabBar.font().bold()
    assert tabBar.font().pointSizeF() > window.font().pointSizeF()

    style = window.tabWidget.styleSheet()
    # A selected-tab accent and a hover state are what make them read as
    # clickable rather than as plain labels.
    assert "QTabBar::tab:selected" in style
    assert "QTabBar::tab:hover" in style


def testMenuBarStructure(window) -> None:
    menuTitles = [action.text() for action in window.menuBar().actions()]
    assert menuTitles == ["&File", "&Password", "&Help"]
    assert [a.text() for a in window.fileMenu.actions()] == ["E&xit"]
    helpItems = [a.text() for a in window.helpMenu.actions() if not a.isSeparator()]
    assert helpItems == ["&Theme", "&About"]


def testThemeMenuOffersSystemLightDark(window) -> None:
    labels = [a.text() for a in window.themeMenu.actions()]
    assert labels == ["Use &System Theme", "&Light", "&Dark"]

    assert all(a.isCheckable() for a in window.themeMenu.actions())
    assert window.themeGroup.isExclusive()
    # Following Windows is the default.
    assert window.themeActions[themeService.systemTheme].isChecked()


def testChoosingDarkAppliesAndRemembersIt(window) -> None:
    window.themeActions[themeService.darkTheme].trigger()

    assert themeService.currentColorScheme() == Qt.ColorScheme.Dark
    assert themeService.loadTheme() == themeService.darkTheme
    assert window.themeActions[themeService.darkTheme].isChecked()
    assert not window.themeActions[themeService.systemTheme].isChecked()


def testChoosingLightAppliesIt(window) -> None:
    window.themeActions[themeService.lightTheme].trigger()

    assert themeService.currentColorScheme() == Qt.ColorScheme.Light
    assert "Light theme applied" in window.statusBar().currentMessage()


def testReturningToSystemReleasesTheOverride(window, qapp) -> None:
    window.themeActions[themeService.lightTheme].trigger()

    window.themeActions[themeService.systemTheme].trigger()

    assert themeService.loadTheme() == themeService.systemTheme
    assert "follows the Windows setting" in window.statusBar().currentMessage()


def testSavedThemeIsRestoredOnNextLaunch(window, qtbot) -> None:
    window.themeActions[themeService.lightTheme].trigger()
    window.close()

    reopened = MainWindow()
    qtbot.addWidget(reopened)

    assert reopened.themeActions[themeService.lightTheme].isChecked()


def testTabStylingFollowsTheNewPalette(window, qtbot) -> None:
    # Regression: the styling used to be rebuilt before Qt delivered the new
    # palette, so switching to Light left the unselected tab label painted in
    # dark-theme white — invisible on a light background.
    window.themeActions[themeService.darkTheme].trigger()
    qtbot.wait(50)
    darkStyle = window.tabWidget.styleSheet()

    window.themeActions[themeService.lightTheme].trigger()
    qtbot.wait(50)

    assert window.tabWidget.styleSheet() != darkStyle


def testSwitchingThemeDoesNotGrowTheTabFont(window) -> None:
    original = window.tabWidget.tabBar().font().pointSizeF()

    for theme in (themeService.darkTheme, themeService.lightTheme, themeService.systemTheme):
        window.themeActions[theme].trigger()

    assert window.tabWidget.tabBar().font().pointSizeF() == pytest.approx(original)


def testPasswordMenuEmptyState(window) -> None:
    window.rebuildPasswordMenu()
    itemTexts = [a.text() for a in window.passwordMenu.actions() if not a.isSeparator()]

    assert itemTexts == [
        "No Passwords Remembered Yet", "&New Password...", "Clear Password History",
    ]
    clearAction = window.passwordMenu.actions()[-1]
    assert not clearAction.isEnabled()


def testPasswordMenuListsMaskedHistory(window) -> None:
    passwordHistoryService.rememberPassword("older-password!")
    passwordHistoryService.rememberPassword("hunter2!")
    window.rebuildPasswordMenu()

    itemTexts = [a.text() for a in window.passwordMenu.actions() if not a.isSeparator()]
    assert itemTexts == [
        "Last Password Used (h...!)",
        "h...!",
        "o...!",
        "&New Password...",
        "Clear Password History",
    ]
    # Only masks appear — never a full password.
    assert all("hunter2!" not in text and "older-password!" not in text for text in itemTexts)


def testPickingMenuEntrySelectsPassword(window) -> None:
    passwordHistoryService.rememberPassword("older-password!")
    passwordHistoryService.rememberPassword("hunter2!")
    window.rebuildPasswordMenu()

    olderEntry = [a for a in window.passwordMenu.actions() if a.text() == "o...!"][0]
    olderEntry.trigger()

    assert window.activePassword == "older-password!"
    assert window.passwordLabel.text() == "Password: o...!"


def testLastPasswordUsedEntrySelectsMostRecent(window) -> None:
    passwordHistoryService.rememberPassword("older-password!")
    passwordHistoryService.rememberPassword("hunter2!")
    window.rebuildPasswordMenu()

    window.passwordMenu.actions()[0].trigger()

    assert window.activePassword == "hunter2!"


def testNewPasswordDialogSelectsPassword(window, monkeypatch) -> None:
    monkeypatch.setattr(PasswordDialog, "getPassword", staticmethod(lambda parent=None: "fresh-pw"))

    window.onNewPassword()

    assert window.activePassword == "fresh-pw"
    assert window.passwordLabel.text() == "Password: f...w"


def testClearPasswordHistory(window) -> None:
    passwordHistoryService.rememberPassword("hunter2!")
    window.usePassword("hunter2!")

    window.onClearPasswordHistory()

    assert passwordHistoryService.loadPasswords() == []
    assert window.activePassword is None
    assert window.passwordLabel.text() == "No password selected"


def testRecopiedSecretIsReprotectedAndPurged(window, qtbot, setClipboard, purgeCalls) -> None:
    setClipboard(encryptText("sensitive", "pw"))
    window.usePassword("pw")
    window.clipboardTab.uncloakButton.click()
    qtbot.waitUntil(lambda: clipboardService.readText() == "sensitive", timeout=5000)
    assert clipboardService.currentTextIsMarkedSecret()

    # Simulate the user re-copying the decrypted text by hand — an ordinary,
    # unmarked copy that Win+V would record.
    qtbot.waitUntil(lambda: clipboardService.writeText("sensitive", secret=False), timeout=5000)

    qtbot.waitUntil(clipboardService.currentTextIsMarkedSecret, timeout=5000)
    assert clipboardService.readText() == "sensitive"
    assert window.lastWriteWasSecret
    qtbot.waitUntil(lambda: bool(purgeCalls), timeout=5000)
    assert "sensitive" in purgeCalls[-1]


def testCloseSweepsSessionSecretsFromHistory(window, qtbot, setClipboard, purgeCalls) -> None:
    setClipboard(encryptText("sensitive", "pw"))
    window.usePassword("pw")
    window.clipboardTab.uncloakButton.click()
    qtbot.waitUntil(lambda: clipboardService.readText() == "sensitive", timeout=5000)
    purgeCalls.clear()

    window.close()

    assert purgeCalls, "closing must sweep session secrets out of Win+V history"
    assert "sensitive" in purgeCalls[-1]


def testClosingClearsAnUncloakedSecret(window, qtbot, setClipboard) -> None:
    setClipboard(encryptText("sensitive", "pw"))
    window.usePassword("pw")
    window.clipboardTab.uncloakButton.click()
    qtbot.waitUntil(lambda: clipboardService.readText() == "sensitive", timeout=5000)

    window.close()

    assert clipboardService.readText() == ""


def testClosingKeepsCloakedTextPasteable(window, qtbot, setClipboard) -> None:
    setClipboard("not secret once encrypted")
    window.usePassword("pw")
    window.clipboardTab.cloakButton.click()
    qtbot.waitUntil(
        lambda: clipboardService.readText() != "not secret once encrypted", timeout=5000
    )
    cloaked = clipboardService.readText()

    window.close()

    assert clipboardService.readText() == cloaked


def testClosingLeavesUnrelatedClipboardAlone(window, qtbot, setClipboard) -> None:
    setClipboard("the user's own clipboard content")

    window.close()

    assert clipboardService.readText() == "the user's own clipboard content"


def testWindowRemembersItsGeometry(window, qtbot) -> None:
    window.resize(701, 503)
    qtbot.waitUntil(lambda: window.size().width() == 701, timeout=5000)

    window.close()

    reopened = MainWindow()
    qtbot.addWidget(reopened)
    reopened.show()

    assert reopened.size() == QSize(701, 503)


def testFirstRunUsesTheDefaultSize(window) -> None:
    # Nothing saved yet (the settings file is isolated per test).
    assert window.size() == QSize(
        appConfig.defaultWindowWidth, appConfig.defaultWindowHeight
    )


def testStrandedWindowIsBroughtBackOnScreen(window, qtbot) -> None:
    # Simulate a saved position on a monitor that is no longer attached.
    window.setGeometry(-9000, -9000, 400, 300)
    window.moveOnScreenIfStranded()

    frame = window.frameGeometry()
    assert any(
        screen.availableGeometry().intersects(frame)
        for screen in QGuiApplication.screens()
    )


def testAboutTextContents(window) -> None:
    aboutText = window.buildAboutText()

    assert "CloakClip" in aboutText
    assert "Version 0.8.0" in aboutText
    assert "Editor: Francois Charette, PhD" in aboutText
    assert "AI Agent: Claude - Fable 5" in aboutText
    assert "Charette AI Group, LLC" in aboutText
