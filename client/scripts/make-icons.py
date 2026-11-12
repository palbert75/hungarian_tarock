"""Draw the app icons (a tarokk card on green felt) without any image library.

Run from the client folder:  python3 scripts/make-icons.py
"""
import struct
import zlib
from pathlib import Path

FELT = (15, 61, 46)
CARD = (250, 248, 240)
EDGE = (139, 127, 209)
GOLD = (202, 138, 4)
INK = (30, 27, 75)

# 5x7 dot letters for "XXI"
GLYPHS = {
    "X": ["10001", "10001", "01010", "00100", "01010", "10001", "10001"],
    "I": ["11111", "00100", "00100", "00100", "00100", "00100", "11111"],
}


def png(size, pixel):
    rows = b"".join(b"\x00" + bytes(c for x in range(size) for c in pixel(x, y)) for y in range(size))

    def chunk(kind, data):
        body = kind + data
        return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body) & 0xFFFFFFFF)

    header = struct.pack(">IIBBBBB", size, size, 8, 2, 0, 0, 0)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header) + chunk(b"IDAT", zlib.compress(rows, 9)) + chunk(b"IEND", b"")


def rounded(x, y, left, top, right, bottom, radius):
    if not (left <= x < right and top <= y < bottom):
        return False
    cx = min(max(x, left + radius), right - radius - 1)
    cy = min(max(y, top + radius), bottom - radius - 1)
    return (x - cx) ** 2 + (y - cy) ** 2 <= radius ** 2


def icon(size, inset):
    """inset: share of the canvas kept free around the card (bigger for maskable icons)."""
    card_h = size * (1 - 2 * inset)
    card_w = card_h * 0.66
    left, top = (size - card_w) / 2, (size - card_h) / 2
    right, bottom = left + card_w, top + card_h
    radius = card_w * 0.12
    border = max(2, size // 64)

    text = "XXI"
    cell = card_w * 0.8 / (len(text) * 6 - 1)
    text_left = (size - cell * (len(text) * 6 - 1)) / 2
    text_top = top + card_h * 0.2

    def pixel(x, y):
        if not rounded(x, y, left, top, right, bottom, radius):
            return FELT
        if not rounded(x, y, left + border, top + border, right - border, bottom - border, radius - border):
            return EDGE
        col, row = (x - text_left) / cell, (y - text_top) / cell
        if 0 <= row < 7 and 0 <= col < len(text) * 6 - 1:
            index, inner = divmod(int(col), 6)
            if inner < 5 and GLYPHS[text[index]][int(row)][inner] == "1":
                return INK
        # A gold diamond in the lower half
        dx, dy = abs(x - size / 2), abs(y - (top + card_h * 0.7))
        if dx / (card_w * 0.2) + dy / (card_h * 0.14) <= 1:
            return GOLD
        return CARD

    return png(size, pixel)


if __name__ == "__main__":
    out = Path(__file__).resolve().parent.parent / "public" / "icons"
    out.mkdir(parents=True, exist_ok=True)
    for name, size, inset in [
        ("icon-192.png", 192, 0.12),
        ("icon-512.png", 512, 0.12),
        ("icon-maskable-512.png", 512, 0.22),
        ("apple-touch-icon.png", 180, 0.12),
    ]:
        (out / name).write_bytes(icon(size, inset))
        print("wrote", out / name)
