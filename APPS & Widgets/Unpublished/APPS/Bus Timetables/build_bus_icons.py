#!/usr/bin/env python3
"""Build Busy Bar app icons for `Bus Timetables`.

The Busy Bar app menu expects:
- `icon_front.bin`: 8x8 LVGL *indexed-color* front icon (LVGL I4).
- `icon_back.bin`: 11x11 LVGL back icon (LVGL I1/1-bit grayscale style).
"""

from __future__ import annotations

import struct
from pathlib import Path

# Back icon header from device samples (magic + WxH + flags + "LpG\0")
# (8x8 front icons are LVGL I4, which uses a different header/layout.)
HDR_11 = bytes([0x19, 0x07, 0x00, 0x00, 0x0B, 0x00, 0x0B, 0x00, 0x02, 0x00, 0x00, 0x00, 0x4C, 0x70, 0x47, 0x00])

DEFAULT_RGBA = bytes([0xE8, 0xBA, 0x10, 0xFF])  # Gold #e8ba10, opaque


def _png_to_lvgl_i4_8x8(png_path: Path) -> tuple[list[list[int]], list[tuple[int, int, int, int]]]:
    """
    Convert a PNG into the Busy Bar front-icon format:
    - 8x8 pixels
    - LVGL indexed-color I4 (4-bit palette indices)
    - index 0 is transparent
    - indices 1.. map to palette colors (we generate up to 2 colors: red and white)
    """
    try:
        from PIL import Image  # type: ignore
    except ImportError as e:  # pragma: no cover
        raise RuntimeError("Pillow (PIL) is required to build icons from PNG sources.") from e

    img = Image.open(png_path).convert("RGBA")
    src_w, src_h = img.size

    # If this is the common app-picker icon size (3x6 from your SVG),
    # place it directly into the 8x8 grid (top-left), without scaling.
    # This prevents the red/white areas from being stretched (which was the
    # cause of the mismatch).
    px = img.load()

    # Palette indices:
    # 0 = transparent
    # 1 = red pixels (bus stop icon "red")
    # 2 = white pixels (bus stop icon "white")
    palette = [
        (0, 0, 0, 0),
        (255, 0, 0, 255),
        (255, 255, 255, 255),
    ] + [(0, 0, 0, 0)] * 13

    def is_redish(r: int, g: int, b: int) -> bool:
        return r > 180 and g < 120 and b < 120

    def is_whiteish(r: int, g: int, b: int) -> bool:
        return r > 180 and g > 180 and b > 180

    pixels: list[list[int]] = [[0] * 8 for _ in range(8)]

    def classify_pixel(x: int, y: int) -> int:
        r, g, b, a = px[x, y]
        if a == 0:
            return 0
        if is_redish(r, g, b):
            return 1
        if is_whiteish(r, g, b):
            return 2
        # Edge/antialias: choose whichever is closer.
        d_red = (r - 255) ** 2 + (g - 0) ** 2 + (b - 0) ** 2
        d_white = (r - 255) ** 2 + (g - 255) ** 2 + (b - 255) ** 2
        return 1 if d_red <= d_white else 2

    if src_w == 3 and src_h == 6:
        # Place the 3x6 SVG-like icon into the 8x8 LVGL canvas.
        # Bus Stop Icon.png is expected to look like:
        #   W RR
        # at the top-left; user request shifts it 2px right.
        x_offset = 2
        for y in range(6):
            for x in range(3):
                dx = x + x_offset
                if 0 <= dx < 8:
                    pixels[y][dx] = classify_pixel(x, y)
    else:
        # Fallback: scale to 8x8 (nearest) if it's not the expected 3x6.
        img8 = img.resize((8, 8), resample=Image.Resampling.NEAREST)
        px8 = img8.load()
        for y in range(8):
            for x in range(8):
                r, g, b, a = px8[x, y]
                if a == 0:
                    pixels[y][x] = 0
                elif is_redish(r, g, b):
                    pixels[y][x] = 1
                elif is_whiteish(r, g, b):
                    pixels[y][x] = 2
                else:
                    d_red = (r - 255) ** 2 + (g - 0) ** 2 + (b - 0) ** 2
                    d_white = (r - 255) ** 2 + (g - 255) ** 2 + (b - 255) ** 2
                    pixels[y][x] = 1 if d_red <= d_white else 2

    return pixels, palette


def write_lvgl_i4_8x8(path: Path, pixels: list[list[int]], palette: list[tuple[int, int, int, int]]) -> None:
    """
    Write an LVGL I4 indexed-color 8x8 image:
    - header = struct.pack('<BBHHHHH', 0x19, 0x09, flags, w, h, stride, reserved)
    - palette = 16 * BGRA entries (little-endian packing <BBBB as b,g,r,a)
    - data = nibble-packed indices (2 pixels per byte, x even in high nibble)
    """
    width = 8
    height = 8
    assert len(pixels) == height and all(len(row) == width for row in pixels)
    assert len(palette) == 16

    cf = 0x09  # LV_COLOR_FORMAT_I4
    stride = (width + 1) // 2  # 2 pixels per byte => 4 bytes for 8px width
    while stride % 4:
        stride += 1

    header = struct.pack(
        "<BBHHHHH",
        0x19,  # magic
        cf,  # color format
        0x0000,  # flags
        width,
        height,
        stride,
        0x0000,  # reserved
    )

    pal_data = bytearray()
    for i in range(16):
        r, g, b, a = palette[i]
        # Palette entries are stored in BGRA byte order.
        pal_data.extend(struct.pack("<BBBB", b, g, r, a))  # BGRA

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


def write_icon_11x11(path: Path, rows_u16: list[int]) -> None:
    assert len(rows_u16) == 11
    body = bytearray()
    for w in rows_u16:
        body += w.to_bytes(2, "little")
    path.write_bytes(HDR_11 + DEFAULT_RGBA + bytes(body))


def main() -> None:
    here = Path(__file__).resolve().parent
    front_png = here / "Bus Stop Icon.png"

    # Front icon: LVGL I4 (108-byte) indexed-color icon expected by Busy Bar menu.
    if not front_png.is_file():
        raise FileNotFoundError(f"Missing: {front_png}")

    pixels, palette = _png_to_lvgl_i4_8x8(front_png)
    write_lvgl_i4_8x8(here / "icon_front.bin", pixels, palette)

    # Back icon builder (existing code) expects an 8x8 bitmask `r8` where each
    # row is packed as MSB=x=0 bits.
    r8: list[int] = []
    for y in range(8):
        row = 0
        for x in range(8):
            if pixels[y][x] != 0:
                row |= 1 << (7 - x)
        r8.append(row)

    # 11x11: centered 8x8 bus with 1px margin, rows as 11 bits in uint16 LE
    def row_11(bits11: int) -> int:
        return bits11 & 0xFFFF

    pad = 1
    r11 = []
    for y in range(11):
        row = 0
        for x in range(11):
            ox = x - pad
            oy = y - pad
            if 0 <= ox < 8 and 0 <= oy < 8:
                bit = (r8[oy] >> (7 - ox)) & 1
                if bit:
                    row |= 1 << (10 - x)
        r11.append(row_11(row))
    write_icon_11x11(here / "icon_back.bin", r11)
    print("Wrote icon_front.bin, icon_back.bin")


if __name__ == "__main__":
    main()
