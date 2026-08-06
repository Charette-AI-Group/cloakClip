"""Tests for the DPAPI-encrypted password history."""

from __future__ import annotations

from pathlib import Path

from cloakClip.services import passwordHistoryService
from platformSkips import needsPasswordStore


def historyFile(tmp_path: Path) -> Path:
    return tmp_path / "passwordHistory.bin"


@needsPasswordStore
def testProtectUnprotectRoundTrip() -> None:
    secret = b"some bytes worth protecting"
    protected = passwordHistoryService.protect(secret)

    assert protected != secret
    assert passwordHistoryService.unprotect(protected) == secret


def testLoadWithoutFileIsEmpty(tmp_path) -> None:
    assert passwordHistoryService.loadPasswords(historyFile(tmp_path)) == []


@needsPasswordStore
def testRememberAndLoad(tmp_path) -> None:
    filePath = historyFile(tmp_path)
    passwordHistoryService.rememberPassword("first!", filePath)
    passwordHistoryService.rememberPassword("second!", filePath)

    assert passwordHistoryService.loadPasswords(filePath) == ["second!", "first!"]


@needsPasswordStore
def testFileOnDiskDoesNotContainPlaintext(tmp_path) -> None:
    filePath = historyFile(tmp_path)
    passwordHistoryService.rememberPassword("VerySecretPassword123", filePath)

    rawBytes = filePath.read_bytes()
    assert b"VerySecretPassword123" not in rawBytes


@needsPasswordStore
def testReuseMovesPasswordToFront(tmp_path) -> None:
    filePath = historyFile(tmp_path)
    for password in ("one", "two", "three"):
        passwordHistoryService.rememberPassword(password, filePath)
    passwordHistoryService.rememberPassword("one", filePath)

    assert passwordHistoryService.loadPasswords(filePath) == ["one", "three", "two"]


@needsPasswordStore
def testHistoryIsCappedAtTen(tmp_path) -> None:
    filePath = historyFile(tmp_path)
    for index in range(13):
        passwordHistoryService.rememberPassword(f"password{index}", filePath)

    passwords = passwordHistoryService.loadPasswords(filePath)
    assert len(passwords) == 10
    assert passwords[0] == "password12"
    assert "password2" not in passwords


@needsPasswordStore
def testEmptyPasswordIsNotStored(tmp_path) -> None:
    filePath = historyFile(tmp_path)
    passwordHistoryService.rememberPassword("real!", filePath)

    passwordHistoryService.rememberPassword("", filePath)

    # Checked against a surviving password rather than an empty history: an
    # empty result is also what a store that cannot write anything returns,
    # so it would not tell the empty password apart from a broken store.
    assert passwordHistoryService.loadPasswords(filePath) == ["real!"]


@needsPasswordStore
def testCorruptFileIsTreatedAsEmpty(tmp_path) -> None:
    filePath = historyFile(tmp_path)
    # Read the history back first. An empty result is what a store that reads
    # nothing at all returns too, so without this the assertion below would
    # hold whether the corruption was salvaged or never even reached.
    passwordHistoryService.rememberPassword("readable!", filePath)
    assert passwordHistoryService.loadPasswords(filePath) == ["readable!"]

    filePath.write_bytes(b"not a DPAPI blob at all")

    assert passwordHistoryService.loadPasswords(filePath) == []


@needsPasswordStore
def testClearPasswordsRemovesFile(tmp_path) -> None:
    filePath = historyFile(tmp_path)
    passwordHistoryService.rememberPassword("soon gone", filePath)
    # Without this, a store that never wrote the file would satisfy every
    # assertion below by having nothing to remove.
    assert filePath.exists()

    passwordHistoryService.clearPasswords(filePath)

    assert not filePath.exists()
    assert passwordHistoryService.loadPasswords(filePath) == []


def testMaskPassword() -> None:
    assert passwordHistoryService.maskPassword("hunter2!") == "h...!"
    assert passwordHistoryService.maskPassword("ab") == "a...b"
    assert passwordHistoryService.maskPassword("x") == "x...x"
    assert passwordHistoryService.maskPassword("") == ""
