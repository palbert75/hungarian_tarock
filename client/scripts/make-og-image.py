"""Make public/og.jpg, the picture messengers show for an invite link (1200x630).

    uv run --no-project --with pillow python scripts/make-og-image.py
"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent.parent
W, H = 1200, 630
FELT_DARK, FELT = (8, 38, 28), (21, 92, 66)
GOLD, CREAM = (250, 204, 21), (245, 240, 225)
SERIF_BOLD = "/System/Library/Fonts/Supplemental/Georgia Bold.ttf"
SERIF = "/System/Library/Fonts/Supplemental/Georgia.ttf"

# Felt: a soft light in the middle, dark towards the corners
felt = Image.new("RGB", (W, H), FELT_DARK)
glow = Image.new("L", (W, H), 0)
ImageDraw.Draw(glow).ellipse((-150, -220, W + 150, H + 220), fill=255)
glow = glow.filter(ImageFilter.GaussianBlur(170))
felt = Image.composite(Image.new("RGB", (W, H), FELT), felt, glow).convert("RGBA")

# A fan of cards on the right
fan = ["hearts-K", "tarokk-I", "tarokk-XXI", "tarokk-skiz", "tarokk-XX"]
card_h = 350
pivot = (905, 800)
for i, name in enumerate(fan):
    art = Image.open(ROOT / "public" / "cards" / f"{name}.webp").convert("RGBA")
    card = art.resize((round(art.width * card_h / art.height), card_h), Image.LANCZOS)
    angle = (i - (len(fan) - 1) / 2) * -11
    # Rotate about a point below the card so the cards fan out
    canvas = Image.new("RGBA", (1700, 1700), (0, 0, 0, 0))
    canvas.alpha_composite(card, (850 - card.width // 2, 850 - 480 - card_h // 2))
    canvas = canvas.rotate(angle, resample=Image.BICUBIC, center=(850, 850))
    shadow = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    shadow.putalpha(canvas.getchannel("A").point(lambda a: a * 0.55))
    shadow = shadow.filter(ImageFilter.GaussianBlur(14))
    offset = (pivot[0] - 850, pivot[1] - 850)
    felt.alpha_composite(shadow, (offset[0] + 8, offset[1] + 14))
    felt.alpha_composite(canvas, offset)

draw = ImageDraw.Draw(felt)
title = ImageFont.truetype(SERIF_BOLD, 132)
lead = ImageFont.truetype(SERIF_BOLD, 50)
small = ImageFont.truetype(SERIF, 32)
x = 70
draw.text((x + 4, 124), "Tarokk", font=title, fill=(0, 0, 0, 140))
draw.text((x, 120), "Tarokk", font=title, fill=GOLD)
draw.line((x, 286, x + 150, 286), fill=GOLD, width=5)
draw.text((x, 322), "Gyere játszani", font=lead, fill=CREAM)
draw.text((x, 384), "az asztalomhoz!", font=lead, fill=CREAM)
draw.text((x, 486), "Magyar tarokk négy játékosnak", font=small, fill=(203, 213, 225))
draw.text((x, 530), "telefonon és gépen", font=small, fill=(203, 213, 225))

felt.convert("RGB").save(ROOT / "public" / "og.jpg", quality=88, optimize=True, progressive=True)
print("public/og.jpg", (ROOT / "public" / "og.jpg").stat().st_size // 1024, "KB")
