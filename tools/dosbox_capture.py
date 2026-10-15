"""Start Keen 1 in DOSBox and capture the DOSBox window at fixed moments.

Used to compare the converter output with the original game (M1, M4).
Screenshots contain id Software graphics, so they go to build/dosbox/ (not in git).

Usage: python tools/dosbox_capture.py [event ...]   (default: 5 15 30 45 60)
An event is either SECONDS (take a screenshot) or SECONDS=KEY[*N] (press a key N times),
e.g. 25=enter 30 31=right*4 35. Keys: enter, space, esc, up, down, left, right, ctrl, alt, f1..f10.
Windows only: uses user32 PrintWindow, which also works when the window is covered.
"""
from __future__ import annotations

import ctypes
import subprocess
import sys
import time
from ctypes import wintypes
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import toolchain as tc  # noqa: E402

ORIGINAL = tc.ROOT / "data" / "original"
OUT = tc.BUILD / "dosbox"
PW_RENDERFULLCONTENT = 2
SCALE = 3

user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32
# Work in physical pixels; otherwise Windows display scaling shrinks the window rectangles.
ctypes.windll.shcore.SetProcessDpiAwareness(2)


def _windows_of(pid: int) -> list[int]:
    found = []

    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def callback(hwnd, _):
        owner = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(owner))
        if owner.value == pid and user32.IsWindowVisible(hwnd):
            found.append(hwnd)
        return True

    user32.EnumWindows(callback, 0)
    return found


def capture(hwnd: int) -> Image.Image:
    rect = wintypes.RECT()
    user32.GetClientRect(hwnd, ctypes.byref(rect))
    w, h = rect.right, rect.bottom
    hdc = user32.GetDC(hwnd)
    mem = gdi32.CreateCompatibleDC(hdc)
    bmp = gdi32.CreateCompatibleBitmap(hdc, w, h)
    gdi32.SelectObject(mem, bmp)
    user32.PrintWindow(hwnd, mem, PW_RENDERFULLCONTENT | 1)   # 1 = client area only
    buf = ctypes.create_string_buffer(w * h * 4)
    info = (ctypes.c_uint32 * 10)(40, w, -h, 1 | (32 << 16), 0, 0, 0, 0, 0, 0)
    gdi32.GetDIBits(mem, bmp, 0, h, buf, info, 0)
    gdi32.DeleteObject(bmp)
    gdi32.DeleteDC(mem)
    user32.ReleaseDC(hwnd, hdc)
    return Image.frombuffer("RGB", (w, h), buf, "raw", "BGRX", 0, 1)


def to_ega(shot: Image.Image) -> Image.Image:
    """Sample the 320x200 screen at pixel centres and snap each pixel to the nearest EGA colour."""
    import numpy as np
    from convert.ega import PALETTE
    w, h = shot.size
    scale = min(w / 320, h / 200)
    left = (w - 320 * scale) / 2
    top = (h - 200 * scale) / 2
    xs = (left + (np.arange(320) + 0.5) * scale).astype(int)
    ys = (top + (np.arange(200) + 0.5) * scale).astype(int)
    rgb = np.asarray(shot.convert("RGB")).astype(int)[ys][:, xs]
    pal = np.array(PALETTE)
    nearest = ((rgb[:, :, None, :] - pal[None, None, :, :]) ** 2).sum(axis=3).argmin(axis=2)
    return Image.fromarray(pal[nearest].astype(np.uint8))


WM_KEYDOWN, WM_KEYUP = 0x0100, 0x0101
# (virtual key, scan code, extended)
KEYS = {
    "enter": (0x0D, 0x1C, False), "space": (0x20, 0x39, False), "esc": (0x1B, 0x01, False),
    "up": (0x26, 0x48, True), "down": (0x28, 0x50, True),
    "left": (0x25, 0x4B, True), "right": (0x27, 0x4D, True),
    "ctrl": (0x11, 0x1D, False), "alt": (0x12, 0x38, False),
    "c": (0x43, 0x2E, False), "t": (0x54, 0x14, False),
    **{f"f{n}": (0x6F + n, 0x3A + n, False) for n in range(1, 11)},
}


def press(hwnd: int, key: str, hold: float = 0.15) -> None:
    vk, scan, extended = KEYS[key]
    lparam = 1 | scan << 16 | (1 << 24 if extended else 0)
    user32.PostMessageW(hwnd, WM_KEYDOWN, vk, lparam)
    time.sleep(hold)
    user32.PostMessageW(hwnd, WM_KEYUP, vk, lparam | 0xC0000000)
    time.sleep(0.1)


def key_event(hwnd: int, key: str, down: bool) -> None:
    vk, scan, extended = KEYS[key]
    lparam = 1 | scan << 16 | (1 << 24 if extended else 0)
    if down:
        user32.PostMessageW(hwnd, WM_KEYDOWN, vk, lparam)
    else:
        user32.PostMessageW(hwnd, WM_KEYUP, vk, lparam | 0xC0000000)


def parse_events(args: list[str]) -> list[tuple[float, str | None, int, float]]:
    """SECONDS, SECONDS=KEY, SECONDS=KEY*COUNT, SECONDS=KEY~HOLD_SECONDS,
    SECONDS=KEY+ (key down), SECONDS=KEY- (key up), SECONDS=burst~DURATION."""
    events = []
    for arg in args:
        moment, _, key = arg.partition("=")
        key, _, hold = key.partition("~")
        key, _, count = key.partition("*")
        events.append((float(moment), key or None, int(count or 1), float(hold or 0.15)))
    return events


PENDING: list[tuple[float, Image.Image]] = []


def burst(hwnd: int, seconds: float, start: float) -> None:
    """Capture as fast as possible; converted and saved after the run (b<milliseconds>.png)."""
    end = time.monotonic() + seconds
    n = 0
    while time.monotonic() < end:
        PENDING.append((time.monotonic() - start, capture(hwnd)))
        n += 1
    print(f"burst: {n} frames in {seconds}s")


def main(events: list[tuple[float, str | None, int, float]]) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    cmd = [tc.dosbox(), "--noprimaryconf", "--nolocalconf",
           "--set", "sdl fullscreen=false", "--set", f"sdl window_size={SCALE * 320}x{SCALE * 200}",
           "--set", "render aspect=false", "--set", "render integer_scaling=false",
           "--set", "render shader=sharp", "--set", "render image_adjustments=off",
           "--set", "dosbox machine=ega",
           "-c", f'mount c "{ORIGINAL}"', "-c", "c:", "-c", "keen1"]
    proc = subprocess.Popen([str(c) for c in cmd])
    start = time.monotonic()
    try:
        for moment, key, count, hold in events:
            time.sleep(max(0.0, start + moment - time.monotonic()))
            windows = _windows_of(proc.pid)
            if not windows:
                print(f"{moment:>5}s: no DOSBox window")
                continue
            if key == "burst":
                burst(windows[0], hold, start)
                continue
            if key and key[-1] in "+-" and len(key) > 1:
                key_event(windows[0], key[:-1], key[-1] == "+")
                continue
            if key:
                for _ in range(count):
                    press(windows[0], key, hold)
                print(f"{moment:>5}s: pressed {key} x{count}")
                continue
            shot = capture(windows[0])
            path = OUT / f"t{int(moment):03d}.png"
            to_ega(shot).save(path)
            print(f"{moment:>5}s: {path} (window {shot.size[0]}x{shot.size[1]})")
    finally:
        proc.terminate()
        for t, shot in PENDING:
            to_ega(shot).save(OUT / f"b{int(t * 1000):06d}.png")


if __name__ == "__main__":
    main(parse_events(sys.argv[1:] or ["5", "15", "30", "45", "60"]))
