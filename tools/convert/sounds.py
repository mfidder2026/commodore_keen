"""PC speaker sound effects in SOUNDS.CK1 (Inverse Frequency Sound format).

Reference: https://moddingwiki.shikadi.net/wiki/Inverse_Frequency_Sound_format
Each sample is a PIT divisor: frequency = 1193181 / value. 0 = silence, $FFFF = end.
"""
from __future__ import annotations

import struct
from dataclasses import dataclass

PIT_HZ = 1193181
END = 0xFFFF


@dataclass
class Sound:
    index: int
    name: str
    priority: int
    rate: int
    samples: list[int]         # PIT divisors, 0 = silence

    def frequencies(self) -> list[float]:
        return [PIT_HZ / s if s else 0.0 for s in self.samples]


def parse(data: bytes) -> list[Sound]:
    signature = data[:4]
    if signature != b"SND\0":
        raise ValueError(f"unexpected sound signature {signature!r}")
    _size, _unknown, count = struct.unpack_from("<HHH", data, 4)
    sounds = []
    for i in range(count):
        entry = 16 + i * 16
        offset, priority, rate = struct.unpack_from("<HBB", data, entry)
        name = data[entry + 4:entry + 16].split(b"\0")[0].decode("ascii", "replace")
        samples = []
        pos = offset
        while True:
            value, = struct.unpack_from("<H", data, pos)
            pos += 2
            if value == END:
                break
            samples.append(value)
        sounds.append(Sound(i + 1, name, priority, rate, samples))
    return sounds
