"""Cut Kumo artwork out of the reference sheets in '../../referencia de modelo/'.

Every character image in the model sheet comes from the reference renders
themselves, so the character is pixel-faithful to the approved design.

Output: ../assets/*.png (transparent background, upscaled with Lanczos).
Usage:  python3 prep.py
"""
from collections import deque
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

HERE = Path(__file__).resolve().parent
REF = HERE.parent.parent / "referencia de modelo"
OUT = HERE.parent / "assets"
OUT.mkdir(exist_ok=True)

R1 = Image.open(REF / "kumo-referencia-01.png").convert("RGB")  # cleaner turnaround
R2 = Image.open(REF / "kumo-referencia-02.png").convert("RGB")  # face + anatomy details


def is_bg(p, sat=40, light=150):
    mx, mn = max(p), min(p)
    return mx - mn < sat and mn > light


def cutout(img, min_hole=30, sat=40, light=150):
    """Transparent background: flood-fill paper-coloured pixels from the border,
    then also clear enclosed paper-coloured holes (arm gaps, inside the spiral)."""
    w, h = img.size
    px = img.load()
    bg = [[is_bg(px[x, y], sat, light) for x in range(w)] for y in range(h)]
    seen = [[False] * w for _ in range(h)]
    clear = [[False] * w for _ in range(h)]

    def flood(sx, sy):
        comp = []
        q = deque([(sx, sy)])
        seen[sy][sx] = True
        while q:
            x, y = q.popleft()
            comp.append((x, y))
            for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                if 0 <= nx < w and 0 <= ny < h and not seen[ny][nx] and bg[ny][nx]:
                    seen[ny][nx] = True
                    q.append((nx, ny))
        return comp

    for y in range(h):
        for x in range(w):
            if bg[y][x] and not seen[y][x]:
                comp = flood(x, y)
                touches = any(px_ in (0, w - 1) or py_ in (0, h - 1) for px_, py_ in comp)
                if touches or len(comp) >= min_hole:
                    for cx, cy in comp:
                        clear[cy][cx] = True
    a = Image.new("L", (w, h), 255)
    ap = a.load()
    for y in range(h):
        for x in range(w):
            if clear[y][x]:
                ap[x, y] = 0
    rgba = img.convert("RGBA")
    rgba.putalpha(a)
    # paper-coloured RGB under transparent pixels would halo when scaled: make it white
    white = Image.new("RGBA", (w, h), (255, 255, 255, 0))
    return Image.composite(rgba, white, a)


def upscale(im, s):
    im = im.resize((im.width * s, im.height * s), Image.LANCZOS)
    rgb = im.convert("RGB").filter(ImageFilter.UnsharpMask(radius=2, percent=60, threshold=2))
    out = rgb.convert("RGBA")
    out.putalpha(im.getchannel("A"))
    return out


def trim(im, pad=4):
    box = im.getchannel("A").point(lambda v: 255 if v > 8 else 0).getbbox()
    box = (max(0, box[0] - pad), max(0, box[1] - pad), min(im.width, box[2] + pad), min(im.height, box[3] + pad))
    return im.crop(box)


def whiten(img):
    """For pencil construction sketches: divide out the paper colour (multiply-style)."""
    bg = (239, 229, 212)
    px = img.load()
    out = img.copy()
    op = out.load()
    for y in range(img.height):
        for x in range(img.width):
            r, g, b = px[x, y]
            v = [min(255, c * 255 // k) for c, k in zip((r, g, b), bg)]
            # lift the paper texture to pure white, keep pencil lines
            v = [255 if c > 226 else int(c * 255 / 226) for c in v]
            op[x, y] = tuple(v)
    return out


def save(im, name):
    im.save(OUT / name)
    print(f"{name:28s} {im.width}x{im.height}")


# ---------------------------------------------------------------- turnaround (ref 01)
strip = cutout(R1.crop((125, 462, 1200, 758)))
alpha = strip.getchannel("A")
cols = [any(alpha.getpixel((x, y)) > 8 for y in range(strip.height)) for x in range(strip.width)]
spans, start = [], None
for x, c in enumerate(cols + [False]):
    if c and start is None:
        start = x
    elif not c and start is not None:
        if x - start > 40:
            spans.append((start, x))
        start = None
names = ["front", "three-quarter", "side", "back"]
assert len(spans) == 4, spans
for (a, b), n in zip(spans, names):
    # keep the full strip height so every view shares the same ground line and scale
    save(upscale(strip.crop((a - 2, 0, b + 2, strip.height)), 3), f"view-{n}.png")

# ---------------------------------------------------------------- face (ref 02, face detail)
face = R2.crop((868, 500, 1020, 636)).copy()
d = ImageDraw.Draw(face)
# erase the dimension leader that touches the lower-left of the head
for i in range(40):
    t = i / 39
    x, y = 4 + (15.5 - 4) * t, 136 + (123 - 136) * t
    d.ellipse((x - 2.6, y - 2.6, x + 2.6, y + 2.6), fill=(239, 229, 212))
face_c = cutout(face)
# drop the neck stubs below the chin
fa = face_c.getchannel("A")
fd = ImageDraw.Draw(fa)
fd.rectangle((0, 134, face_c.width, face_c.height), fill=0)
fd.rectangle((0, 0, face_c.width, 4), fill=0)
fd.rectangle((0, 0, 12, 50), fill=0)  # dimension-line ticks
fd.rectangle((139, 0, face_c.width, 50), fill=0)
face_c.putalpha(fa)
save(upscale(face_c, 4), "face-front.png")  # 608 x 544, crop space x4


# ---------------------------------------------------------------- anatomy details (ref 02)
details = {
    "arm": (853, 893, 927, 997),
    "hand": (1003, 903, 1077, 1007),
    "leg": (1168, 888, 1262, 992),
    "foot": (851, 1060, 932, 1152),
}
for n, box in details.items():
    save(upscale(trim(cutout(R2.crop(box))), 3), f"detail-{n}.png")

# eye detail: keep only the eye disc (drop leader lines)
eye = cutout(R2.crop((854, 714, 944, 804)))
m = Image.new("L", eye.size, 0)
ImageDraw.Draw(m).ellipse((2, 2, 88, 88), fill=255)
eye.putalpha(Image.composite(eye.getchannel("A"), m, m))
save(upscale(trim(eye), 4), "detail-eye.png")

for n, box in {
    "construction": (18, 124, 928, 316),
    "snout": (1098, 703, 1202, 792),
    "tail-side": (1016, 1052, 1093, 1133),
    "tail-back": (1183, 1052, 1268, 1157),
}.items():
    im = whiten(R2.crop(box))
    save(im.resize((im.width * 2, im.height * 2), Image.LANCZOS), f"sketch-{n}.png")
