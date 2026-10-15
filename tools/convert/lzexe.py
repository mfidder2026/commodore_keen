"""LZEXE 0.91 unpacker.

Reference: Scott Smitelli, "LZEXE", https://cosmodoc.org/topics/lzexe/
Returns the decompressed load image (without relocation fixups applied) and the
relocation table, which together are what UNLZEXE writes back as a plain EXE.
"""
from __future__ import annotations

import struct
from dataclasses import dataclass

LZEXE_HEADER_SIZE = 14
RELOC_TABLE_OFFSET = 0x158      # LZEXE header + decompressor code, in the decompressor segment


@dataclass
class UnpackedExe:
    image: bytes                          # load image, as DOS would have loaded the plain EXE
    relocations: list[tuple[int, int]]    # (segment, offset) pairs
    cs: int
    ip: int
    ss: int
    sp: int


class _Bits:
    """LZEXE flag buffer: 16-bit little-endian words, consumed LSB first."""

    def __init__(self, data: bytes, pos: int):
        self.data = data
        self.pos = pos
        self._load()

    def _load(self) -> None:
        self.buf = self.data[self.pos] | self.data[self.pos + 1] << 8
        self.pos += 2
        self.count = 16

    def bit(self) -> int:
        b = self.buf & 1
        self.buf >>= 1
        self.count -= 1
        if self.count == 0:
            self._load()
        return b

    def byte(self) -> int:
        b = self.data[self.pos]
        self.pos += 1
        return b


def is_lzexe(exe: bytes) -> bool:
    return exe[:2] == b"MZ" and exe[0x1C:0x20] in (b"LZ91", b"LZ09")


def unpack(exe: bytes) -> UnpackedExe:
    if exe[0x1C:0x20] != b"LZ91":
        raise ValueError("not an LZEXE 0.91 executable")
    header_paragraphs, = struct.unpack_from("<H", exe, 0x08)
    ip, cs = struct.unpack_from("<HH", exe, 0x14)
    loaded = exe[header_paragraphs * 16:]

    stub = cs * 16                         # the LZEXE header sits at CS:0000
    real_ip, real_cs, real_sp, real_ss = struct.unpack_from("<HHHH", loaded, stub)

    out = bytearray()
    bits = _Bits(loaded, 0)
    while True:
        if bits.bit():                     # 1: literal byte
            out.append(bits.byte())
            continue
        if not bits.bit():                 # 00xx: short distance
            length = (bits.bit() << 1 | bits.bit()) + 2
            distance = bits.byte() - 256
        else:                              # 01: long distance
            lo = bits.byte()
            hi = bits.byte()
            distance = (lo | (hi & 0xF8) << 5) - 8192
            length = hi & 0x07
            if length:
                length += 2
            else:
                code = bits.byte()
                if code == 0:
                    break                  # end of data
                if code == 1:
                    continue               # segment change; no effect on a flat buffer
                length = code + 1
        start = len(out) + distance
        if start < 0:
            raise ValueError("LZEXE back reference before start of data")
        for i in range(length):            # byte by byte: overlapping copies are runs
            out.append(out[start + i])

    relocations = _read_relocations(loaded, stub + RELOC_TABLE_OFFSET)
    return UnpackedExe(bytes(out), relocations, real_cs, real_ip, real_ss, real_sp)


def _read_relocations(data: bytes, pos: int) -> list[tuple[int, int]]:
    relocations = []
    segment = 0
    offset = 0
    while True:
        step = data[pos]
        pos += 1
        if step == 0:
            step, = struct.unpack_from("<H", data, pos)
            pos += 2
            if step == 0:
                segment += 0x0FFF
                continue
            if step == 1:
                return relocations
        offset += step
        segment += offset >> 4             # normalise like the decompressor does
        offset &= 0x0F
        relocations.append((segment, offset))
