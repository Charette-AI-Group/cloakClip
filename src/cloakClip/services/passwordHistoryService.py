"""Recently used passwords, stored encrypted with Windows DPAPI.

DPAPI ties the encryption to the current Windows user account: the file is
unreadable from other accounts or machines, but any program running as this
user can decrypt it. That is the standard trade-off for "remember my
password" features; the Clear Password History menu item exists for users
who want nothing kept.
"""

from __future__ import annotations

import ctypes
import json
import logging
from ctypes import wintypes
from pathlib import Path

from cloakClip import appConfig

logger = logging.getLogger(__name__)

cryptProtectUiForbidden = 0x1


class DataBlob(ctypes.Structure):
    _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_char))]


def _crypt32():
    return ctypes.WinDLL("crypt32", use_last_error=True)


def _takeBlobBytes(blob: DataBlob) -> bytes:
    try:
        return ctypes.string_at(blob.pbData, blob.cbData)
    finally:
        ctypes.WinDLL("kernel32", use_last_error=True).LocalFree(blob.pbData)


def _dpapiCall(functionName: str, data: bytes) -> bytes:
    buffer = ctypes.create_string_buffer(data, len(data))
    inBlob = DataBlob(len(data), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_char)))
    outBlob = DataBlob()
    function = getattr(_crypt32(), functionName)
    ok = function(
        ctypes.byref(inBlob), None, None, None, None,
        cryptProtectUiForbidden, ctypes.byref(outBlob),
    )
    if not ok:
        raise OSError(f"{functionName} failed (error {ctypes.get_last_error()})")
    return _takeBlobBytes(outBlob)


def protect(data: bytes) -> bytes:
    return _dpapiCall("CryptProtectData", data)


def unprotect(data: bytes) -> bytes:
    return _dpapiCall("CryptUnprotectData", data)


def maskPassword(password: str) -> str:
    """'hunter2!' -> 'h...!' — enough to jog the memory, nothing more."""
    if not password:
        return ""
    return f"{password[0]}...{password[-1]}"


def _historyFile(filePath: Path | None) -> Path:
    return filePath if filePath is not None else appConfig.passwordHistoryFile


def loadPasswords(filePath: Path | None = None) -> list[str]:
    """Most recent first. Missing or unreadable history is just empty."""
    historyFile = _historyFile(filePath)
    if not historyFile.exists():
        return []
    try:
        passwords = json.loads(unprotect(historyFile.read_bytes()).decode("utf-8"))
    except (OSError, ValueError, UnicodeDecodeError):
        logger.warning("Password history unreadable; starting fresh", exc_info=True)
        return []
    if not isinstance(passwords, list):
        return []
    return [p for p in passwords if isinstance(p, str)][: appConfig.maxPasswordHistory]


def rememberPassword(password: str, filePath: Path | None = None) -> list[str]:
    """Put a password at the front of the history; returns the new history."""
    if not password:
        return loadPasswords(filePath)
    passwords = loadPasswords(filePath)
    if password in passwords:
        passwords.remove(password)
    passwords.insert(0, password)
    passwords = passwords[: appConfig.maxPasswordHistory]

    historyFile = _historyFile(filePath)
    historyFile.parent.mkdir(parents=True, exist_ok=True)
    historyFile.write_bytes(protect(json.dumps(passwords).encode("utf-8")))
    return passwords


def clearPasswords(filePath: Path | None = None) -> None:
    historyFile = _historyFile(filePath)
    if historyFile.exists():
        historyFile.unlink()
