#!/usr/bin/env python3
"""Build Busy Bar launcher `icon_front.bin` (8×8 LVGL I4) for Water Timer.

Draws a 1-pixel-outline cup with blue fill (no external PNG required).
Back icon: `app.json` `back_icon` points at a shared device asset.
"""

from __future__ import annotations

import struct
from pathlib import Path


def write_lvgl_i4_8x8(path: Path, pixels: list[list[int]], palette: list[tuple[int, int, int, int]]) -> None:
    width = 8
    height = 8
    assert len(pixels) == height and all(len(row) == width for row in pixels)
    assert len(palette) == 16

    cf = 0x09
    stride = (width + 1) // 2
    while stride % 4:
        stride += 1

    header = struct.pack("<BBHHHHH", 0x19, cf, 0x0000, width, height, stride, 0x0000)
    pal_data = bytearray()
    for i in range(16):
        r, g, b, a = palette[i]
        pal_data.extend(struct.pack("<BBBB", b, g, r, a))

    data = bytearray()
    for y in range(height):
        row = bytearray(stride)
        for x in range(width):
            idx = pixels[y][x] & 0x0F
            byte_pos = x // 2
            if x % 2 == 0:
                row[byte_pos] |= idx << 4
            else:
                row[byte_pos] |= idx
        data.extend(row)

    path.write_bytes(header + pal_data + data)


def cup_icon_8x8_pixels() -> tuple[list[list[int]], list[tuple[int, int, int, int]]]:
    """1px outline, blue fill. Closed square (no open top), shifted 1px down in the 8×8 cell."""
    # Palette: 0 transparent, 1 white, 2 blue, rest unused
    palette = [
        (0, 0, 0, 0),
        (255, 255, 255, 255),
        (55, 140, 230, 255),
    ] + [(0, 0, 0, 0)] * 13

    p = [[0] * 8 for _ in range(8)]
    # 4×4 closed box at x=2..5, y=1..4 (full top + bottom; one row lower than old open cup)
    for x in range(2, 6):
        p[1][x] = 1
    for y in range(2, 4):
        p[y][2] = 1
        p[y][5] = 1
        p[y][3] = 2
        p[y][4] = 2
    for x in range(2, 6):
        p[4][x] = 1
    return p, palette


def main() -> None:
    here = Path(__file__).resolve().parent
    pixels, palette = cup_icon_8x8_pixels()
    out = here / "icon_front.bin"
    write_lvgl_i4_8x8(out, pixels, palette)
    print(f"Wrote {out} (8x8 LVGL I4: closed square cup, 1px lower)")


if __name__ == "__main__":
    main()
