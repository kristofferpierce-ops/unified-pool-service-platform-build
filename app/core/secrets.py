"""Field-level secret handling for sensitive source cells (e.g. vendor TAXID).

Two operations:
  keyed_hash(normalized) -> a pepper-keyed HMAC, used as a *match/dedup key* for a
      sensitive value without storing it (an EIN/SSN is a ~9-digit space, so a bare
      or per-row-salted digest is trivially enumerable; a server-side pepper is not).
  encrypt/decrypt        -> reversible at-rest storage so no-loss holds for a
      sensitive value while it never appears in any query/review surface.

Keys come from the environment (UPS_FIELD_ENCRYPTION_KEY / UPS_TAXID_HASH_PEPPER)
and must live OUTSIDE the database. A dev default is used when unset so a local
desktop install and the test suite work out of the box; PRODUCTION MUST set both
env vars (the dev key is in source, so it is obfuscation, not protection).

Implementation note: the platform ships no crypto library, so this uses a stdlib
encrypt-then-MAC construction (HMAC-SHA256 keystream in counter mode + an
HMAC-SHA256 tag, verified with compare_digest). If `cryptography` (Fernet) is
later added, swap the two _stdlib_* calls for it without changing callers.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import os

_DEV_KEY = 'ups-dev-field-key-not-for-production'
_DEV_PEPPER = 'ups-dev-taxid-pepper-not-for-production'
_MAGIC = b'UPSv1'


def production_key_configured() -> bool:
    return bool(os.environ.get('UPS_FIELD_ENCRYPTION_KEY'))


def _kek() -> bytes:
    return hashlib.sha256((os.environ.get('UPS_FIELD_ENCRYPTION_KEY') or _DEV_KEY).encode()).digest()


def _pepper() -> bytes:
    return (os.environ.get('UPS_TAXID_HASH_PEPPER') or _DEV_PEPPER).encode()


def norm_sensitive(value: str) -> str:
    """Normalize a sensitive value for hashing/dedup (digits + letters, upper)."""
    return ''.join(ch for ch in (value or '') if ch.isalnum()).upper()


def keyed_hash(normalized: str) -> str:
    if not normalized:
        return ''
    return hmac.new(_pepper(), normalized.encode(), hashlib.sha256).hexdigest()


def _keystream(key: bytes, nonce: bytes, length: int) -> bytes:
    out = bytearray()
    counter = 0
    while len(out) < length:
        out += hmac.new(key, nonce + counter.to_bytes(8, 'big'), hashlib.sha256).digest()
        counter += 1
    return bytes(out[:length])


def encrypt(plaintext: str) -> str:
    key = _kek()
    nonce = os.urandom(16)
    data = plaintext.encode('utf-8')
    ct = bytes(a ^ b for a, b in zip(data, _keystream(key, nonce, len(data))))
    tag = hmac.new(key, _MAGIC + nonce + ct, hashlib.sha256).digest()
    return base64.b64encode(nonce + ct + tag).decode('ascii')


def decrypt(token: str) -> str:
    blob = base64.b64decode(token.encode('ascii'))
    nonce, ct, tag = blob[:16], blob[16:-32], blob[-32:]
    key = _kek()
    expected = hmac.new(key, _MAGIC + nonce + ct, hashlib.sha256).digest()
    if not hmac.compare_digest(tag, expected):
        raise ValueError('cipher tag mismatch (wrong key or tampered ciphertext)')
    return bytes(a ^ b for a, b in zip(ct, _keystream(key, nonce, len(ct)))).decode('utf-8')
