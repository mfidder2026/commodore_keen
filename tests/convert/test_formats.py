"""M1: decoders tested on synthetic data, so no id Software data is needed or stored."""
from __future__ import annotations

import random
import struct

from tools.convert import keen_lzw, levels, lzexe, sounds, tileinfo


# --- RLEW -------------------------------------------------------------------

def test_rlew_literals_and_runs():
    words = [1, 2, 0xFEFE, 3, 3, 3, 3, 3, 7]
    packed = struct.pack("<I", len(words) * 2) + struct.pack(
        "<14H", 1, 2, 0xFEFE, 1, 0xFEFE, 0xFEFE, 5, 3, 7, 0, 0, 0, 0, 0)
    assert levels.rlew_decompress(packed) == struct.pack(f"<{len(words)}H", *words)


def test_level_parse_planes():
    width, height = 3, 2
    plane_size = 16                                       # 2*w*h rounded up to 16
    header = struct.pack("<HHH4x4xH16x", width, height, 2, plane_size)
    tiles = struct.pack("<6H", 1, 2, 3, 4, 5, 6).ljust(plane_size, b"\0")
    sprites = struct.pack("<6H", 0, 0, 255, 0, 9, 0).ljust(plane_size, b"\0")
    raw = header + tiles + sprites
    words = struct.unpack(f"<{len(raw) // 2}H", raw)
    lvl = levels.parse(1, struct.pack("<I", len(raw)) + struct.pack(f"<{len(words)}H", *words))
    assert lvl.tiles == [[1, 2, 3], [4, 5, 6]]
    assert lvl.sprites == [[0, 0, 255], [0, 9, 0]]


# --- Keen LZW -----------------------------------------------------------------

def lzw_compress(data: bytes, max_bits: int = 12) -> bytes:
    """Reference encoder producing the Keen 1 LZW layout the decoder expects."""
    max_entries = 1 << max_bits
    table = {bytes([i]): i for i in range(256)}
    next_code = keen_lzw.FIRST_FREE
    codes = []
    current = b""
    for byte in data:
        candidate = current + bytes([byte])
        if candidate in table:
            current = candidate
            continue
        codes.append(table[current])
        if next_code < max_entries:
            table[candidate] = next_code
            next_code += 1
        current = bytes([byte])
    if current:
        codes.append(table[current])
    codes.append(keen_lzw.CODE_END)

    # Emit with the code width the decoder will be using at each point.
    bits = []
    width = 9
    decoder_next = keen_lzw.FIRST_FREE
    for i, code in enumerate(codes):
        bits.extend((code >> (width - 1 - b)) & 1 for b in range(width))
        if i >= 1 and code != keen_lzw.CODE_END and decoder_next < max_entries:
            decoder_next += 1
            if decoder_next == (1 << width) - 1 and width < max_bits:
                width += 1
    bits.extend([0] * (-len(bits) % 8))
    body = bytes(int("".join(map(str, bits[i:i + 8])), 2) for i in range(0, len(bits), 8))
    return struct.pack("<IH", len(data), max_bits) + body + b"\0\0"


def test_lzw_small():
    data = b"ABABABABABAAAAAAAAAB"
    assert keen_lzw.decompress(lzw_compress(data)) == data


def test_lzw_grows_to_12_bits_and_fills_dictionary():
    rng = random.Random(1)
    words = [bytes(rng.randrange(256) for _ in range(rng.randrange(2, 9))) for _ in range(300)]
    data = b"".join(rng.choice(words) for _ in range(6000))   # enough to fill all 4096 entries
    assert keen_lzw.decompress(lzw_compress(data)) == data


# --- LZEXE --------------------------------------------------------------------

def make_lzexe(stream: bytes, relocs: bytes) -> bytes:
    """Minimal LZEXE 0.91 file: MZ header, compressed stream, LZEXE stub with relocation table."""
    body = stream.ljust((len(stream) + 15) // 16 * 16, b"\0")
    cs = len(body) // 16
    stub = struct.pack("<HHHHHHH", 0x0010, 0x0002, 0x0080, 0x0003, cs, 0, 0)   # real IP, CS, SP, SS ...
    stub = stub.ljust(lzexe.RELOC_TABLE_OFFSET, b"\x90") + relocs
    header = bytearray(32)
    header[0:2] = b"MZ"
    struct.pack_into("<H", header, 0x08, 2)              # header size: 2 paragraphs
    struct.pack_into("<HH", header, 0x14, 0x000E, cs)    # IP after the 14-byte LZEXE header
    header[0x1C:0x20] = b"LZ91"
    return bytes(header) + body + stub


def test_lzexe_literals_short_copy_and_end():
    # Flag bits, LSB first: 1 1 (literals A, B), 0 0 1 1 (short copy, length 5), 0 1 (long code).
    flags = 0b10110011
    stream = struct.pack("<H", flags) + b"AB" + bytes([0xFE]) + bytes([0x00, 0x00, 0x00])
    exe = make_lzexe(stream, bytes([0x05, 0x00, 0x01, 0x00]))
    assert lzexe.is_lzexe(exe)
    unpacked = lzexe.unpack(exe)
    assert unpacked.image == b"ABABABA"
    assert unpacked.relocations == [(0, 5)]
    assert (unpacked.cs, unpacked.ip, unpacked.ss, unpacked.sp) == (2, 0x10, 3, 0x80)


def test_lzexe_long_copy_with_length_byte():
    # 1 (literal X), 0 1 (long), then lo/hi with length bits 000 and a length byte.
    flags = 0b101
    distance = -1 & 0x1FFF                               # 13-bit two's complement
    lo = distance & 0xFF
    hi = (distance >> 8) << 3                            # length bits 000 -> length byte follows
    stream = struct.pack("<H", flags) + b"X" + bytes([lo, hi, 9])
    # End code after it: flags continue in the same word: 0 1 then 00 00 00.
    flags = 0b101 | 0b10 << 3
    stream = struct.pack("<H", flags) + b"X" + bytes([lo, hi, 9]) + bytes([0, 0, 0])
    unpacked = lzexe.unpack(make_lzexe(stream, bytes([0x00, 0x01, 0x00])))
    assert unpacked.image == b"X" * 11


# --- Tileinfo and sounds -----------------------------------------------------

def test_tileinfo_planes():
    count = 2
    planes = [(1, 4), (0, 1), (1, 0), (0, 1), (1, 1), (0, 0)]
    image = b"pad" + b"".join(struct.pack("<2h", *p) for p in planes)
    info = tileinfo.read(image, count, offset=3)
    assert info[0] == tileinfo.TileInfo(1, 0, 1, 0, 1, 0)
    assert info[1] == tileinfo.TileInfo(4, 1, 0, 1, 1, 0)


def test_sounds_parse():
    samples = [1000, 0, 2000]
    data_offset = 32
    header = b"SND\0" + struct.pack("<HHH", 0, 0x3C, 1) + bytes(6)
    entry = struct.pack("<HBB", data_offset, 200, 8) + b"BEEPSND".ljust(12, b"\0")
    body = struct.pack("<4H", *samples, 0xFFFF)
    parsed = sounds.parse(header + entry + body)
    assert len(parsed) == 1
    assert parsed[0].name == "BEEPSND" and parsed[0].priority == 200
    assert parsed[0].samples == samples
    assert parsed[0].frequencies()[0] == sounds.PIT_HZ / 1000
