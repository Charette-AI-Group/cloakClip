"""Password-based text encryption for clipboard content.

Wire-compatible with the original PowerShell scripts (encrypt.ps1 /
decrypt.ps1): AES-256-CBC, key = SHA-256(password), random 16-byte IV
prepended to the ciphertext, whole payload Base64-encoded. Strings
encrypted by either tool decrypt in the other.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import os

from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

ivSize = 16
blockSizeBits = 128


class CryptoError(Exception):
    """Raised when decryption fails; the message is safe to show in the UI."""


def deriveKey(password: str) -> bytes:
    return hashlib.sha256(password.encode("utf-8")).digest()


def encryptText(plainText: str, password: str) -> str:
    key = deriveKey(password)
    iv = os.urandom(ivSize)

    padder = padding.PKCS7(blockSizeBits).padder()
    paddedBytes = padder.update(plainText.encode("utf-8")) + padder.finalize()

    encryptor = Cipher(algorithms.AES(key), modes.CBC(iv)).encryptor()
    cipherBytes = encryptor.update(paddedBytes) + encryptor.finalize()

    return base64.b64encode(iv + cipherBytes).decode("ascii")


def decryptText(encodedText: str, password: str) -> str:
    try:
        payload = base64.b64decode(encodedText.strip(), validate=True)
    except (binascii.Error, ValueError) as exc:
        raise CryptoError("The clipboard does not contain an encrypted text.") from exc

    cipherLength = len(payload) - ivSize
    if cipherLength < ivSize or cipherLength % ivSize != 0:
        raise CryptoError("The clipboard does not contain an encrypted text.") from None

    iv, cipherBytes = payload[:ivSize], payload[ivSize:]
    decryptor = Cipher(algorithms.AES(deriveKey(password)), modes.CBC(iv)).decryptor()
    paddedBytes = decryptor.update(cipherBytes) + decryptor.finalize()

    unpadder = padding.PKCS7(blockSizeBits).unpadder()
    try:
        plainBytes = unpadder.update(paddedBytes) + unpadder.finalize()
        return plainBytes.decode("utf-8")
    except (ValueError, UnicodeDecodeError) as exc:
        raise CryptoError("Wrong password (or the text was not encrypted by CloakClip).") from exc
