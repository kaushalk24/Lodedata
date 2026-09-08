"""Deobfuscation of the .ntw network-file payload.

Everything after the 512-byte header is scrambled with a fixed 100-byte
additive keystream:

    cipher[i] = (plain[i] + KEY[i % 100]) & 0xFF

The key is a constant baked into the application -- it is byte-for-byte
identical in every sample file, regardless of licence, user or design.
It was recovered from the long stretches of untouched (all-zero)
pre-allocated table space that every design file contains.
"""

NTW_KEY = bytes.fromhex(
    "5d7e57377b74352c3915272eca57591d29175c4f2384292d30371140762b4651"
    "3c2f7182647e5620103d4cab73603e616d24c41b2b5d6fd2d75464156a4c6463"
    "9611726b167e435a353f5f35747be4445d155928ad54c42f123cb2182ed73e18"
    "162a69c2"
)
KEY_LEN = len(NTW_KEY)          # 100
PAYLOAD_START = 512


def deobfuscate(payload: bytes, phase: int = 0) -> bytes:
    """Turn the raw bytes that follow the header into plain records."""
    k = NTW_KEY
    return bytes((b - k[(i + phase) % KEY_LEN]) & 0xFF for i, b in enumerate(payload))


def obfuscate(plain: bytes, phase: int = 0) -> bytes:
    """Inverse of :func:`deobfuscate` -- for writing files back out."""
    k = NTW_KEY
    return bytes((b + k[(i + phase) % KEY_LEN]) & 0xFF for i, b in enumerate(plain))


def open_ntw(path) -> tuple[bytes, bytes]:
    """Return ``(header, plain_payload)`` for a .ntw file on disk."""
    data = open(path, "rb").read()
    return data[:PAYLOAD_START], deobfuscate(data[PAYLOAD_START:])


def recover_key(payload: bytes, key_len: int = KEY_LEN) -> bytes:
    """Re-derive the keystream from a file, for verifying it never changes.

    Finds the longest run that repeats with the key period -- that run is
    untouched pre-allocated space, i.e. plaintext zeros, so the ciphertext
    there *is* the key.
    """
    best_len = best_start = 0
    run = 0
    start = 0
    for i in range(len(payload) - key_len):
        if payload[i] == payload[i + key_len]:
            if run == 0:
                start = i
            run += 1
            if run > best_len:
                best_len, best_start = run, start
        else:
            run = 0
    if best_len < key_len:
        raise ValueError("no periodic run long enough to recover the key")
    key = bytearray(key_len)
    for j in range(key_len):
        key[(best_start + j) % key_len] = payload[best_start + j]
    return bytes(key)
