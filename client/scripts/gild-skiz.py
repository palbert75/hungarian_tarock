"""Make the skíz golden: a deep yellow ground and a gold frame; the figure keeps its colours.

Start from the painted skíz that slice-cards.py cuts (not from an already golden one).
From the client folder:

    uv run --no-project --with pillow --with numpy python scripts/gild-skiz.py \
        <painted tarokk-skiz.webp> public/cards/tarokk-skiz.webp <compare.png> public/cards/tarokk-XXI.webp
"""
import sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

src, out, preview = sys.argv[1], sys.argv[2], sys.argv[3]
im = Image.open(src).convert("RGBA")
a = np.asarray(im).astype(np.float32)
rgb, alpha = a[..., :3], a[..., 3:]

# The pale parchment: bright and little colour. Weight 1 there, fading to 0 on the drawing.
mx, mn = rgb.max(-1), rgb.min(-1)
light = np.clip((mn - 120) / 70, 0, 1)          # bright
pale = np.clip(1 - (mx - mn - 45) / 50, 0, 1)   # unsaturated
ground = (light * pale)[..., None]
ground = np.asarray(Image.fromarray((ground[..., 0] * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.2))).astype(np.float32)[..., None] / 255

gold_light = np.array([250, 205, 85], np.float32)   # the new ground
shade = rgb.mean(-1, keepdims=True) / 245             # keep the paper's texture
golden = np.clip(gold_light * (0.80 + 0.22 * shade), 0, 255)
rgb2 = rgb * (1 - ground) + golden * ground
# A warm glaze over everything, lighter on the figure
rgb2 = rgb2 * np.array([1.0, 0.97, 0.82], np.float32)

res = Image.fromarray(np.concatenate([np.clip(rgb2, 0, 255), alpha], -1).astype(np.uint8), "RGBA")

# Gold frame just inside the rounded edge: dark gold line, bright gold line
w, h = res.size
frame = Image.new("RGBA", res.size, (0, 0, 0, 0))
d = ImageDraw.Draw(frame)
d.rounded_rectangle([5, 5, w - 6, h - 6], radius=16, outline=(150, 100, 10, 255), width=5)
d.rounded_rectangle([7, 7, w - 8, h - 8], radius=14, outline=(250, 205, 60, 255), width=2)
d.rounded_rectangle([13, 13, w - 14, h - 14], radius=10, outline=(176, 124, 20, 200), width=1)
res = Image.alpha_composite(res, frame)
res.putalpha(Image.fromarray(alpha[..., 0].astype(np.uint8)))   # keep the transparent corners
res.save(out, quality=84, method=6)

# Before / after, next to another card
other = Image.open(sys.argv[4]).convert("RGBA")
sheet = Image.new("RGBA", (w * 3 + 40, h + 20), (22, 101, 52, 255))
for i, card in enumerate([im, res, other]):
    sheet.alpha_composite(card, (10 + i * (w + 10), 10))
sheet.convert("RGB").save(preview)
