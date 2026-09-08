"""Reader library for Lode Data Design Assistant binary files.

Reverse engineered from sample files; see docs/file-formats.md for the
evidence behind every field decoded here.
"""
from .header import LodeHeader, read_header, FILE_KINDS
from .obfuscation import NTW_KEY, deobfuscate, obfuscate
from .specs import (
    CableSpec, CouplerSpec, ActiveSpec, TapSpec,
    read_cables, read_couplers, read_actives, read_taps, SpecSet,
)

__all__ = [
    "LodeHeader", "read_header", "FILE_KINDS",
    "NTW_KEY", "deobfuscate", "obfuscate",
    "CableSpec", "CouplerSpec", "ActiveSpec", "TapSpec",
    "read_cables", "read_couplers", "read_actives", "read_taps", "SpecSet",
]
