"""Tests for the main window: tabs, menus, passwords, exit behavior."""

from __future__ import annotations

import pytest
from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtTest import QTest

from cloakClip import appConfig
from cloakClip.services import clipboardService, passwordHistoryService, themeService
from cloakClip.services.cryptoService import encryptText
from cloakClip.services.platform.clipboardBackend import ClipboardBackend
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
    assert [a.text() for a in window.fileMenu.actions()] == [
        "E&xit", "Exit and Clear &All!"
    ]
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


def testGuardDoesNotRewriteWhenMarkingIsUnavailable(window, monkeypatch) -> None:
    """The guard reacts to its own re-write, so it needs a way to settle.

    Marking is that way: once the text is marked the guard returns early. A
    backend that cannot mark never reaches that state, and the guard used to
    answer its own write with another one until the stack ran out. The write
    count is capped here so a regression fails the assertion instead of
    recursing until pytest chokes on the traceback.
    """
    monkeypatch.setattr(clipboardService, "backend", ClipboardBackend())
    writes: list[str] = []
    realWriteText = clipboardService.writeText

    def countedWriteText(text: str, secret: bool = False) -> bool:
        writes.append(text)
        if len(writes) > 20:
            return True
        return realWriteText(text, secret=secret)

    monkeypatch.setattr(clipboardService, "writeText", countedWriteText)
    window.sessionSecrets.add("sensitive")

    clipboardService.writeText("sensitive", secret=True)

    assert writes == ["sensitive"], (
        f"the guard answered its own clipboard write {len(writes) - 1} more time(s)"
    )


def testCloseSweepsSessionSecretsFromHistory(window, qtbot, setClipboard, purgeCalls) -> None:
    setClipboard(encryptText("sensitive", "pw"))
    window.usePassword("pw")
    window.clipboardTab.uncloakButton.click()
    qtbot.waitUntil(lambda: clipboardService.readText() == "sensitive", timeout=5000)
    purgeCalls.clear()

    window.close()

    assert purgeCalls, "closing must sweep session secrets out of Win+V history"
    assert "sensitive" in purgeCalls[-1]


def testExitAndClearAllEmptiesEverything(window, qtbot, setClipboard, historyCalls) -> None:
    setClipboard("something left over")
    window.manualTab.plainEdit.setPlainText("draft note")

    window.exitAndClearAction.trigger()

    assert clipboardService.readText() == ""
    assert historyCalls, "Exit and Clear All must purge clipboard history"
    assert window.manualTab.plainEdit.toPlainText() == ""
    assert window.clipboardTab.previewEdit.toPlainText() == ""
    assert not window.isVisible()


def testExitAndClearAllDoesNotAskAgain(window, monkeypatch) -> None:
    asked: list[int] = []
    monkeypatch.setattr(
        MainWindow, "askCloseAction", lambda self: asked.append(1) or "close"
    )

    window.exitAndClearAction.trigger()

    assert not asked, "the user already said how they wanted to exit"


def testCloseDialogOffersBothChoicesAndCancel(window) -> None:
    box = window.buildCloseDialog()

    labels = {button.text() for button in box.buttons()}
    assert labels == {"OK", "OK - Clear All!", "Cancel"}
    assert box.defaultButton() is window.closeOkButton
    box.deleteLater()


def testEscapeOnTheCloseDialogCancels(window, qtbot) -> None:
    # Regression: with no RejectRole button, QMessageBox assigns no escape
    # button, so Escape and the dialog's own X silently did nothing.
    box = window.buildCloseDialog()
    qtbot.addWidget(box)
    assert box.escapeButton() is window.closeCancelButton

    box.show()
    qtbot.waitExposed(box)
    QTest.keyClick(box, Qt.Key.Key_Escape)

    # Windows fires the escape button outright, but macOS animates the click,
    # so the button lands roughly 100ms after the key rather than during it.
    # Waiting covers both; on Windows the condition already holds.
    qtbot.waitUntil(lambda: box.clickedButton() is not None, timeout=5000)
    assert box.clickedButton() is window.closeCancelButton
    assert window.closeActionFor(box.clickedButton()) is None


def testCloseChoiceMapping(window) -> None:
    window.buildCloseDialog().deleteLater()

    assert window.closeActionFor(window.closeOkButton) == "close"
    assert window.closeActionFor(window.closeClearButton) == "clearAndClose"
    assert window.closeActionFor(window.closeCancelButton) is None
    assert window.closeActionFor(None) is None


def testCloseDialogClearAllPurgesHistory(window, qtbot, setClipboard, monkeypatch,
                                         historyCalls) -> None:
    monkeypatch.setattr(MainWindow, "askCloseAction", lambda self: "clearAndClose")
    setClipboard("leftover secret")

    window.close()

    assert clipboardService.readText() == ""
    assert historyCalls, "the Clear All choice must purge clipboard history"
    assert not window.isVisible()


def testCloseDialogPlainOkLeavesHistoryAlone(window, qtbot, setClipboard,
                                             historyCalls) -> None:
    # The default stub returns "close".
    setClipboard("the user's own clipboard content")

    window.close()

    assert clipboardService.readText() == "the user's own clipboard content"
    assert not historyCalls
    assert not window.isVisible()


def testDismissingTheCloseDialogKeepsTheWindowOpen(window, monkeypatch) -> None:
    monkeypatch.setattr(MainWindow, "askCloseAction", lambda self: None)

    window.close()

    assert window.isVisible(), "Escape on the close dialog must cancel the exit"


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
