"""Keen 1 LZW decompression, used for EGALATCH.CK1 and EGASPRIT.CK1.

Reference: https://moddingwiki.shikadi.net/wiki/LZW_Compression (Commander Keen 1-3 section)
Layout: uint32 decompressed size, uint16 maximum code width (12), then MSB-first
codes starting at 9 bits. Code $100 is an error marker and $101 ends the data.
"""
from __future__ import annotations

import struct

CODE_ERROR = 0x100
CODE_END = 0x101
FIRST_FREE = 0x102


def decompress(data: bytes) -> bytes:
    size, max_bits = struct.unpack_from("<IH", data, 0)
    bitpos = 6 * 8
    total_bits = len(data) * 8
    width = 9
    max_entries = 1 << max_bits

    # Dictionary entries as (prefix code, last byte); roots are single bytes.
    prefix = [-1] * max_entries
    suffix = list(range(256)) + [0] * (max_entries - 256)
    next_code = FIRST_FREE

    def string(code: int) -> bytes:
        out = bytearray()
        while code >= 0:
            out.append(suffix[code])
            code = prefix[code]
        out.reverse()
        return bytes(out)

    def read_code() -> int:
        nonlocal bitpos
        if bitpos + width > total_bits:
            raise ValueError("LZW data ended without end code")
        byte = bitpos >> 3
        chunk = int.from_bytes(data[byte:byte + 3], "big")
        chunk >>= 24 - width - (bitpos & 7)
        bitpos += width
        return chunk & ((1 << width) - 1)

    out = bytearray()
    previous = None
    while True:
        code = read_code()
        if code == CODE_END:
            break
        if code == CODE_ERROR:
            raise ValueError("LZW error marker in data")
        if previous is None:
            entry = string(code)
        else:
            if code < next_code:
                entry = string(code)
                first = entry[0]
            else:                                   # KwKwK: code being defined right now
                prev = string(previous)
                first = prev[0]
                entry = prev + bytes([first])
            if next_code < max_entries:
                prefix[next_code] = previous
                suffix[next_code] = first
                next_code += 1
                if next_code == (1 << width) - 1 and width < max_bits:
                    width += 1
        out += entry
        previous = code

    if len(out) != size:
        raise ValueError(f"LZW size mismatch: got {len(out)}, header says {size}")
    return bytes(out)
