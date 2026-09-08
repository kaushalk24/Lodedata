"""The 512-byte header shared by every Lode Data file."""
from dataclasses import dataclass

HEADER_SIZE = 512

# magic string -> (extension, human name)
FILE_KINDS = {
    "Lode Data Network File":    ("ntw", "Network design"),
    "Lode Data Actives File":    ("atv", "Active devices (amplifiers/nodes)"),
    "Lode Data Cables File":     ("cbl", "Cable types"),
    "Lode Data Couplers File":   ("cpr", "Couplers / splitters / power inserters"),
    "Lode Data Taps File":       ("tap", "Taps"),
    "Lode Data Parameters File": ("par", "System design parameters"),
}


def _cstr(buf: bytes) -> str:
    return buf.split(b"\0", 1)[0].decode("latin-1").strip()


@dataclass
class LodeHeader:
    magic: str
    kind: str            # short extension-style kind, "" when unrecognised
    description: str
    format_major: int    # byte 26 -- 12 for ntw/atv, 11 for cbl/cpr/par/tap
    format_minor: int    # byte 27 -- 1 in every sample seen
    app_version: str     # e.g. "Design 12.11"; only .ntw fills this in
    license_id: str      # e.g. "LP-13X00J3" -- the dongle/licence the file came from
    user_id: str         # e.g. "vk1091", "SEASTMAN", "CCJ"
    raw: bytes

    @property
    def format_version(self) -> str:
        return f"{self.format_major}.{self.format_minor}"


def read_header(data: bytes) -> LodeHeader:
    if len(data) < HEADER_SIZE:
        raise ValueError("file is shorter than the 512-byte Lode Data header")
    magic = _cstr(data[0:26])
    kind, desc = FILE_KINDS.get(magic, ("", "unknown"))
    return LodeHeader(
        magic=magic,
        kind=kind,
        description=desc,
        format_major=data[26],
        format_minor=data[27],
        app_version=_cstr(data[28:128]),
        license_id=_cstr(data[129:145]),
        user_id=_cstr(data[145:161]),
        raw=data[:HEADER_SIZE],
    )
