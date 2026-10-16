"""Minimal client for the VICE binary monitor (x64sc -binarymonitor), for debugging hangs:
read the CPU registers and memory of a running emulator.

Protocol: https://vice-emu.sourceforge.io/vice_13.html (binary monitor, API version 2).
"""
from __future__ import annotations

import socket
import struct
import time

API = 0x02
CMD_MEMORY_GET = 0x01
CMD_REGISTERS_GET = 0x31
CMD_EXIT = 0xAA


class Monitor:
    def __init__(self, host: str = "127.0.0.1", port: int = 6502, timeout: float = 20.0):
        deadline = time.monotonic() + timeout
        while True:
            try:
                self.sock = socket.create_connection((host, port), timeout=5)
                break
            except OSError:
                if time.monotonic() > deadline:
                    raise
                time.sleep(0.2)
        self.request_id = 0

    def _send(self, command: int, body: bytes = b"") -> int:
        self.request_id += 1
        header = struct.pack("<BBIIB", 0x02, API, len(body), self.request_id, command)
        self.sock.sendall(header + body)
        return self.request_id

    def _recv_exact(self, n: int) -> bytes:
        data = b""
        while len(data) < n:
            chunk = self.sock.recv(n - len(data))
            if not chunk:
                raise ConnectionError("monitor closed")
            data += chunk
        return data

    def _response(self, request_id: int) -> tuple[int, bytes]:
        """Read responses until the one for request_id (events are skipped)."""
        while True:
            head = self._recv_exact(12)
            _, _, length, rtype, error, rid = struct.unpack("<BBIBBI", head)
            body = self._recv_exact(length)
            if rid == request_id:
                if error:
                    raise RuntimeError(f"monitor error {error:#x} for command {rtype:#x}")
                return rtype, body

    def registers(self) -> dict[int, int]:
        rid = self._send(CMD_REGISTERS_GET, b"\x00")
        _, body = self._response(rid)
        count, = struct.unpack_from("<H", body, 0)
        regs, pos = {}, 2
        for _ in range(count):
            size, reg_id, value = struct.unpack_from("<BBH", body, pos)
            regs[reg_id] = value
            pos += size + 1
        return regs

    def memory(self, start: int, end: int) -> bytes:
        rid = self._send(CMD_MEMORY_GET, struct.pack("<BHHBH", 0, start, end, 0, 0))
        _, body = self._response(rid)
        length, = struct.unpack_from("<H", body, 0)
        return body[2:2 + length]

    def resume(self) -> None:
        self._send(CMD_EXIT)

    def close(self) -> None:
        self.sock.close()


# Register ids of the C64 main CPU (VICE): A, X, Y, PC, SP, flags.
REG_A, REG_X, REG_Y, REG_PC, REG_SP, REG_FLAGS = 0x00, 0x01, 0x02, 0x03, 0x04, 0x05
