"""Cut the card art sheets into single cards with transparent corners (WebP).

Needs Pillow and numpy. From the client folder:

    uv run --no-project --with pillow --with numpy python scripts/slice-cards.py <folder with the sheets> public/cards

The folder holds sheet1.png … sheet6.png (tarokk I–VIII, IX–XVI, XVII–skíz,
clubs, hearts, diamonds) and grid.png (the small overview of the whole deck,
used for spades because there is no large spades sheet).
"""
import sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

SRC = Path(sys.argv[1])
OUT = Path(sys.argv[2]); OUT.mkdir(parents=True, exist_ok=True)
WIDTH = 320

def bands(profile, min_len, thresh):
    on = profile > thresh
    out, start = [], None
    for i, v in enumerate(on):
        if v and start is None: start = i
        if not v and start is not None:
            if i - start >= min_len: out.append((start, i))
            start = None
    if start is not None and len(on) - start >= min_len: out.append((start, len(on)))
    return out

def find_cards(im, min_w, min_h):
    a = np.asarray(im.convert("RGB")).astype(int)
    bg = np.median(a[:6, :6].reshape(-1, 3), axis=0)
    mask = (np.abs(a - bg).max(axis=2) > 22)
    boxes = []
    for (y0, y1) in bands(mask.sum(axis=1), min_h, 12):
        for (x0, x1) in bands(mask[y0:y1].sum(axis=0), min_w, 12):
            sub = mask[y0:y1, x0:x1]
            ys = np.where(sub.sum(axis=1) > 6)[0]
            boxes.append((x0, y0 + ys[0], x1, y0 + ys[-1] + 1))
    return boxes

def cut(im, box, name):
    x0, y0, x1, y1 = box
    pad = 3
    crop = im.convert("RGB").crop((x0 - pad, y0 - pad, x1 + pad, y1 + pad))
    # Everything reachable from the corners without crossing the card's edge is background
    marker = (255, 0, 255)
    work = crop.copy()
    w, h = work.size
    for seed in ((0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)):
        ImageDraw.floodfill(work, seed, marker, thresh=38)
    alpha = Image.fromarray((np.any(np.asarray(work) != marker, axis=2) * 255).astype("uint8"))
    alpha = alpha.filter(ImageFilter.MinFilter(3)).filter(ImageFilter.GaussianBlur(0.8))
    card = crop.convert("RGBA"); card.putalpha(alpha)
    # One shape for the whole deck (5:8), so cards line up in the hand
    card = card.resize((WIDTH, WIDTH * 8 // 5), Image.LANCZOS)
    card.save(OUT / f"{name}.webp", quality=84, method=6)
    return card.size, float(np.asarray(alpha).mean() / 255)

SHEETS = {
    "sheet1": ["tarokk-I", "tarokk-II", "tarokk-III", "tarokk-IV", "tarokk-V", "tarokk-VI", "tarokk-VII", "tarokk-VIII"],
    "sheet2": ["tarokk-IX", "tarokk-X", "tarokk-XI", "tarokk-XII", "tarokk-XIII", "tarokk-XIV", "tarokk-XV", "tarokk-XVI"],
    "sheet3": ["tarokk-XVII", "tarokk-XVIII", "tarokk-XIX", "tarokk-XX", "tarokk-XXI", "tarokk-skiz"],
    "sheet4": ["clubs-K", "clubs-Q", "clubs-C", "clubs-J", "clubs-10"],
    "sheet5": ["hearts-K", "hearts-Q", "hearts-C", "hearts-J", "hearts-10"],
    "sheet6": ["diamonds-K", "diamonds-Q", "diamonds-C", "diamonds-J", "diamonds-10"],
}
for sheet, names in SHEETS.items():
    im = Image.open(SRC / f"{sheet}.png")
    boxes = find_cards(im, 200, 300)
    assert len(boxes) == len(names), (sheet, len(boxes), boxes)
    for box, name in zip(boxes, names):
        print(name, box, *cut(im, box, name))

# Spades exist only on the small overview sheet
im = Image.open(SRC / "grid.png")
boxes = find_cards(im, 40, 70)
print("grid cards", len(boxes))
rows = {}
for b in boxes: rows.setdefault(b[1] // 40, []).append(b)
ordered = [sorted(r) for _, r in sorted(rows.items())]
print([len(r) for r in ordered])
spades = ordered[2][5:10]
for box, name in zip(spades, ["spades-K", "spades-Q", "spades-C", "spades-J", "spades-10"]):
    print(name, box, *cut(im, box, name))

# The overview draws the spade king with a club: take the symbol from the queen
king = Image.open(OUT / "spades-K.webp").convert("RGBA")
queen = Image.open(OUT / "spades-Q.webp").convert("RGBA")
symbol = (66, 30, 150, 118)
king.paste(queen.crop(symbol), symbol[:2])
king.save(OUT / "spades-K.webp", quality=84, method=6)
