"""Tests for the DPAPI-encrypted password history."""

from __future__ import annotations

from pathlib import Path

from cloakClip.services import passwordHistoryService


def historyFile(tmp_path: Path) -> Path:
    return tmp_path / "passwordHistory.bin"


def testProtectUnprotectRoundTrip() -> None:
    secret = b"some bytes worth protecting"
    protected = passwordHistoryService.protect(secret)

    assert protected != secret
    assert passwordHistoryService.unprotect(protected) == secret


def testLoadWithoutFileIsEmpty(tmp_path) -> None:
    assert passwordHistoryService.loadPasswords(historyFile(tmp_path)) == []


def testRememberAndLoad(tmp_path) -> None:
    filePath = historyFile(tmp_path)
    passwordHistoryService.rememberPassword("first!", filePath)
    passwordHistoryService.rememberPassword("second!", filePath)

    assert passwordHistoryService.loadPasswords(filePath) == ["second!", "first!"]


def testFileOnDiskDoesNotContainPlaintext(tmp_path) -> None:
    filePath = historyFile(tmp_path)
    passwordHistoryService.rememberPassword("VerySecretPassword123", filePath)

    rawBytes = filePath.read_bytes()
    assert b"VerySecretPassword123" not in rawBytes


def testReuseMovesPasswordToFront(tmp_path) -> None:
    filePath = historyFile(tmp_path)
    for password in ("one", "two", "three"):
        passwordHistoryService.rememberPassword(password, filePath)
    passwordHistoryService.rememberPassword("one", filePath)

    assert passwordHistoryService.loadPasswords(filePath) == ["one", "three", "two"]


def testHistoryIsCappedAtTen(tmp_path) -> None:
    filePath = historyFile(tmp_path)
    for index in range(13):
        passwordHistoryService.rememberPassword(f"password{index}", filePath)

    passwords = passwordHistoryService.loadPasswords(filePath)
    assert len(passwords) == 10
    assert passwords[0] == "password12"
    assert "password2" not in passwords


def testEmptyPasswordIsNotStored(tmp_path) -> None:
    filePath = historyFile(tmp_path)
    passwordHistoryService.rememberPassword("", filePath)

    assert passwordHistoryService.loadPasswords(filePath) == []


def testCorruptFileIsTreatedAsEmpty(tmp_path) -> None:
    filePath = historyFile(tmp_path)
    filePath.write_bytes(b"not a DPAPI blob at all")

    assert passwordHistoryService.loadPasswords(filePath) == []


def testClearPasswordsRemovesFile(tmp_path) -> None:
    filePath = historyFile(tmp_path)
    passwordHistoryService.rememberPassword("soon gone", filePath)

    passwordHistoryService.clearPasswords(filePath)

    assert not filePath.exists()
    assert passwordHistoryService.loadPasswords(filePath) == []


def testMaskPassword() -> None:
    assert passwordHistoryService.maskPassword("hunter2!") == "h...!"
    assert passwordHistoryService.maskPassword("ab") == "a...b"
    assert passwordHistoryService.maskPassword("x") == "x...x"
    assert passwordHistoryService.maskPassword("") == ""
