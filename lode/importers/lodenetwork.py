"""Reader for Lode Data's ``.ntw`` network (design) files.

**Status: the container is solved, the record layout is not.**  This module
deobfuscates a network file and lets you inspect it; it does **not** yet
reconstruct plant topology, because doing that on a guess would hand you a
design that is not yours.  What is known is written down here so the work can
be finished as soon as a known-plaintext sample is available.

What is established
-------------------
*Header* -- 512 bytes, same shape as the spec files: a title
(``Lode Data Network File``), a version string (``Design 12.11``), a licence
and a user name.

*Body* -- obfuscated by XOR against a **fixed 100-byte keystream** that is
constant across files: all four sample networks from one operator, of four
different sizes, share it byte for byte.  The period was measured, not
guessed: at lag 100 the ciphertext self-matches on 93.98% of bytes, against
about 2.9% at every other lag up to 700.

The keystream is recovered from the file itself.  A design file is mostly
unused record slots holding one repeated template, so the most common 100-byte
block *is* the keystream XOR that template; XOR every block against it and
about 96% of the body becomes zero, which is what real sparse structured data
looks like.

The mask is **arithmetic, not XOR**.  Decoding four files together, the
differences from the template are 0, +-1, +-16, +-32, +-48, +-63 and +-64,
and the XOR view of the same bytes gives 1, 3, 7, 15, 31, 63, 127 -- the
borrow-propagation pattern you get from adding and subtracting, not from
XOR.  ``0xFF`` then reads as the usual "unset" sentinel, which it does:
it is the second most common decoded byte.

What is not established, and why
--------------------------------
**The payload is not a fixed-field record table.**  That is proved, not
assumed.  Profiling every byte position across 4,768 non-template records
from four files, all one hundred positions have the same statistics: about
84% zero with top values 255/63/47 on even positions and 72% zero with
255/64/16 on odd ones.  In a real record format a footage column and a
device column look nothing alike.  Per-position entropy is flat -- about
0.30 bits at *every* candidate width from 4 to 200 bytes, spread 0.02 to
0.29 -- where a genuine record width would show a large spread.

So the 100-byte period is the repeat length of the idle pattern, not a
record size, and the payload is a packed or variable-length stream whose
fields do not sit at fixed offsets.  Its dominant motifs are three zero
bytes followed by ``0x40``, and ``0xFF`` pairs.

Recovering a serialisation grammar of that kind is not reachable by
statistics alone; it needs **known plaintext**.  One small design whose
footages, tap values and house counts can be read off Lode Data's own
screen will do it, and two saves differing by a single edit will do it
faster, because the bytes that move *are* that field.  Until then this
module reports rather than pretends.

:func:`profile` reproduces the analysis above so the finding can be
re-checked against other files rather than taken on trust.
"""

from __future__ import annotations

import collections
import os
from dataclasses import dataclass, field

HEADER = 512
PERIOD = 100


@dataclass
class NetworkFile:
    """A deobfuscated ``.ntw`` file, ready to inspect."""

    path: str = ""
    title: str = ""
    version: str = ""
    licence: str = ""
    user: str = ""
    raw: bytes = b""
    plain: bytes = b""
    keystream: bytes = b""
    #: how strongly the body repeats at the keystream period
    period_confidence: float = 0.0
    notes: list = field(default_factory=list)

    @property
    def zero_fraction(self) -> float:
        return self.plain.count(0) / len(self.plain) if self.plain else 0.0

    def clusters(self, gap: int = 40) -> list:
        """Runs of non-zero plaintext, which is where the design lives."""
        out, start, prev = [], None, None
        for index, byte in enumerate(self.plain):
            if not byte:
                continue
            if start is None:
                start = prev = index
                continue
            if index - prev > gap:
                out.append((start, prev))
                start = index
            prev = index
        if start is not None:
            out.append((start, prev))
        return out

    def summary(self) -> str:
        clusters = self.clusters()
        lines = [
            f"{os.path.basename(self.path)}  {len(self.raw):,} bytes",
            f"  {self.title}   {self.version}",
            f"  licence {self.licence}   user {self.user}",
            f"  keystream  period {PERIOD}, self-match "
            f"{self.period_confidence * 100:.2f}%  "
            f"[{self.keystream[:8].hex()}...]",
            f"  body       {len(self.plain):,} bytes, "
            f"{self.zero_fraction * 100:.1f}% zero after deobfuscation",
            f"  data       {len(clusters)} clusters, "
            f"{sum(b - a + 1 for a, b in clusters):,} non-zero bytes",
        ]
        for note in self.notes:
            lines.append(f"  ! {note}")
        return "\n".join(lines)

    def dump(self, limit: int = 6, width: int = 160) -> str:
        """Hex of the largest data clusters, for mapping fields by eye."""
        out = []
        biggest = sorted(self.clusters(), key=lambda r: r[1] - r[0],
                         reverse=True)[:limit]
        for start, end in biggest:
            seg = self.plain[start:end + 1]
            out.append(f"\ncluster @{start} length {len(seg)}")
            for off in range(0, min(len(seg), width), 16):
                chunk = seg[off:off + 16]
                text = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)
                out.append(f"  +{off:<5} "
                           f"{' '.join(f'{b:02x}' for b in chunk):<47} |{text}|")
        return "\n".join(out)


def _text(buf: bytes, off: int, length: int) -> str:
    return buf[off:off + length].split(b"\x00")[0].decode("latin1",
                                                          "replace").strip()


def keystream_of(raw: bytes) -> bytes:
    """Recover the obfuscation keystream from the file's own template runs."""
    counts = collections.Counter(
        raw[i:i + PERIOD] for i in range(HEADER, len(raw) - PERIOD, PERIOD))
    if not counts:
        return b"\x00" * PERIOD
    return counts.most_common(1)[0][0]


def period_confidence(raw: bytes, period: int = PERIOD,
                      sample: int = 200000) -> float:
    """Fraction of body bytes that repeat at *period* -- the periodicity proof."""
    body = raw[HEADER:HEADER + sample]
    if len(body) <= period:
        return 0.0
    matches = sum(1 for i in range(len(body) - period)
                  if body[i] == body[i + period])
    return matches / (len(body) - period)


def read_network(path: str) -> NetworkFile:
    raw = open(path, "rb").read()
    key = keystream_of(raw)
    plain = bytes((raw[i] - key[(i - HEADER) % PERIOD]) & 0xFF
                  for i in range(HEADER, len(raw)))
    net = NetworkFile(
        path=os.path.abspath(path), title=_text(raw, 0, 28),
        version=_text(raw, 28, 32), licence=_text(raw, 129, 16),
        user=_text(raw, 145, 16), raw=raw, plain=plain, keystream=key,
        period_confidence=period_confidence(raw),
    )
    net.notes.append(
        "the mask is arithmetic, not XOR: differences from the template are "
        "0, +-1, +-16, +-32, +-48, +-63, +-64, and 0xFF reads as 'unset'.")
    net.notes.append(
        "the payload is NOT a fixed-record table -- per-position entropy is "
        "flat at every candidate width from 4 to 200 bytes. Run "
        "'lode inspect-network --profile' to reproduce that. Topology cannot "
        "be reconstructed from these files alone.")
    net.notes.append(
        "to finish it, supply known plaintext -- a small design whose "
        "footages, tap values and house counts you can read off Lode Data's "
        "screen, or two saves differing by one edit.")
    return net


def profile(paths, width: int = PERIOD) -> str:
    """Field-structure test: is the payload a fixed-record table?

    Decodes with the arithmetic mask, then reports per-position statistics
    and per-position entropy across a range of candidate record widths.  A
    real fixed-field format shows a *large* entropy spread between positions;
    a flat spread at every width means the fields are not at fixed offsets.
    """
    import math

    records = []
    for path in paths:
        raw = open(path, "rb").read()
        key = keystream_of(raw)
        body = raw[HEADER:]
        blocks = [body[i:i + PERIOD]
                  for i in range(0, len(body) - PERIOD + 1, PERIOD)]
        records += [bytes((c - k) & 0xFF for c, k in zip(b, key))
                    for b in blocks if b != key]
    if not records:
        return "no non-template records found"

    out = [f"{len(records)} non-template records from {len(paths)} file(s)",
           "", "candidate record widths (a real one shows a LARGE spread):",
           "  width   mean entropy   spread"]
    stream = b"".join(records)
    for candidate in (4, 8, 10, 16, 20, 25, 50, 100, 128, 200):
        entropies = []
        for position in range(candidate):
            column = collections.Counter(
                stream[i] for i in range(position, len(stream), candidate))
            total = sum(column.values()) or 1
            entropies.append(
                -sum(c / total * math.log2(c / total) for c in column.values()))
        spread = max(entropies) - min(entropies)
        entropies_mean = sum(entropies) / len(entropies)
        out.append(f"  {candidate:>5}   {entropies_mean:>12.3f}   {spread:>6.3f}")

    out += ["", f"per-position profile over {width} bytes:",
            "  pos  distinct  zero%   top decoded values"]
    for position in range(min(width, PERIOD)):
        column = collections.Counter(r[position] for r in records)
        top = " ".join(f"{v}x{c}" for v, c in column.most_common(4) if v)
        out.append(f"  {position:>3}  {len(column):>8}  "
                   f"{column[0] / len(records) * 100:>5.1f}%  {top}")
    out += ["",
            "Flat statistics across every position mean the payload is a",
            "packed or variable-length stream, not a fixed-record table."]
    return "\n".join(out)


def compare(paths) -> str:
    """Do these files share a keystream?  They should; it is a constant."""
    rows, keys = [], {}
    for path in paths:
        raw = open(path, "rb").read()
        key = keystream_of(raw)
        keys[path] = key
        rows.append(f"  {os.path.basename(path):<16} {len(raw):>9,} bytes   "
                    f"keystream {key[:8].hex()}")
    shared = len(set(keys.values())) == 1
    rows.append(f"\n  all files share one keystream: {shared}")
    if shared:
        rows.append("  -> the obfuscation constant is program-wide, not "
                    "per-file, so it can be applied to any .ntw")
    return "\n".join(rows)
