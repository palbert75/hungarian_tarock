"""Turn the engraved jester picture into the skíz card, shaped like the rest of the deck.

From the client folder:

    uv run --no-project --with pillow --with numpy python scripts/make-skiz.py <jester.png> public/cards/tarokk-skiz.webp [compare.png]

The card is cut out along its black outer edge (the edge itself goes too, like the
other cards have none), the corners become transparent, the white paper takes the
deck's cream tone and the card is brought to the deck's 5:8 shape at 320 px wide.
"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

SRC, OUT = Path(sys.argv[1]), Path(sys.argv[2])
COMPARE = Path(sys.argv[3]) if len(sys.argv) > 3 else None
CARDS = OUT.parent
WIDTH = 320

src = Image.open(SRC).convert("RGB")

# Background = what the corners reach without crossing the black outer edge
marker = (255, 0, 255)
work = src.copy()
w, h = work.size
for seed in ((0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)):
    ImageDraw.floodfill(work, seed, marker, thresh=60)
inside = Image.fromarray((np.any(np.asarray(work) != marker, axis=2) * 255).astype("uint8"))
# Step in past the black edge line (about 7 px at this size), then soften like the other cards
alpha = inside.filter(ImageFilter.MinFilter(19)).filter(ImageFilter.GaussianBlur(1.5))
box = alpha.getbbox()

# The deck's paper colour: the light pixels of a few other cards
paper = []
for name in ("hearts-K", "tarokk-XXI", "clubs-Q"):
    a = np.asarray(Image.open(CARDS / f"{name}.webp").convert("RGBA")).reshape(-1, 4).astype(float)
    a = a[(a[:, 3] > 250) & (a[:, :3].min(1) > 200)]
    paper.append(np.median(a[:, :3], axis=0))
cream = np.mean(paper, axis=0)

rgb = np.asarray(src).astype(float) * (cream / 255.0)   # white -> cream, the ink stays
card = Image.fromarray(np.clip(rgb, 0, 255).astype("uint8")).convert("RGBA")
card.putalpha(alpha)
card = card.crop(box).resize((WIDTH, WIDTH * 8 // 5), Image.LANCZOS)
card.save(OUT, quality=84, method=6)
print("paper", cream.round(), "card", card.size)

if COMPARE:
    others = [Image.open(CARDS / f"{n}.webp").convert("RGBA") for n in ("tarokk-XXI", "hearts-K")]
    sheet = Image.new("RGBA", (WIDTH * 3 + 40, WIDTH * 8 // 5 + 20), (22, 101, 52, 255))
    for i, c in enumerate([card] + others):
        sheet.alpha_composite(c, (10 + i * (WIDTH + 10), 10))
    sheet.convert("RGB").save(COMPARE)
