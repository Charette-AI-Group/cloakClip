"""Tests for the crypto service, including PowerShell wire-compatibility."""

from __future__ import annotations

import base64

import pytest

from cloakClip.services import cryptoService
from cloakClip.services.cryptoService import CryptoError, decryptText, encryptText

# Produced by the original encrypt.ps1 algorithm (AES-256-CBC, SHA-256 key,
# IV prepended) with the password below — proves cross-tool compatibility.
powershellCipherText = (
    "I6tzNSHj+89kzsw+3bwgi5QDSoVT/UHMEgFxAgyZeN1jccAP8Gvl2+UKyW0N0n9QV4NBkDLJ6fcmUJPFWxLXuA=="
)
powershellPassword = "Correct-Horse-42!"
powershellPlainText = "Attack at dawn — café résumé ☕"


def testRoundTrip() -> None:
    encrypted = encryptText("Hello, CloakClip!", "hunter2!")
    assert decryptText(encrypted, "hunter2!") == "Hello, CloakClip!"


def testRoundTripMultilineUnicode() -> None:
    text = "line one\nline two — naïve 日本語\n\ttabbed"
    encrypted = encryptText(text, "pässwörd ☂")
    assert decryptText(encrypted, "pässwörd ☂") == text


def testRandomIvProducesDifferentCipherText() -> None:
    first = encryptText("same text", "same password")
    second = encryptText("same text", "same password")
    assert first != second
    assert decryptText(first, "same password") == decryptText(second, "same password")


def testDecryptsPowershellEncryptedString() -> None:
    assert decryptText(powershellCipherText, powershellPassword) == powershellPlainText


def testWrongPasswordRaises() -> None:
    encrypted = encryptText("secret", "right password")
    with pytest.raises(CryptoError, match="Wrong password"):
        decryptText(encrypted, "wrong password")


def testNotBase64Raises() -> None:
    with pytest.raises(CryptoError, match="does not contain"):
        decryptText("this is plain text, not base64!", "any")


def testTooShortPayloadRaises() -> None:
    onlyIv = base64.b64encode(b"\x00" * cryptoService.ivSize).decode("ascii")
    with pytest.raises(CryptoError, match="does not contain"):
        decryptText(onlyIv, "any")


def testMisalignedPayloadRaises() -> None:
    misaligned = base64.b64encode(b"\x00" * (cryptoService.ivSize * 2 + 3)).decode("ascii")
    with pytest.raises(CryptoError, match="does not contain"):
        decryptText(misaligned, "any")


def testDecryptIgnoresSurroundingWhitespace() -> None:
    encrypted = encryptText("padded paste", "pw")
    assert decryptText(f"  {encrypted}\n", "pw") == "padded paste"
