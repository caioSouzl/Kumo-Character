"""Prepare single-subject Rodin input images from transparent view cut-outs.

    python3 prepare_views.py --views DIR [--face FACE.png] --out OUTDIR [--size 1024]

DIR must contain view-front.png, view-three-quarter.png, view-side.png, view-back.png
(transparent PNGs). Writes square PNGs on white plus a contact sheet `_sheet.png`.
"""
import argparse
import os

from PIL import Image


def square(im, size, fill=0.88):
    im = im.convert("RGBA")
    bb = im.getchannel("A").getbbox()
    if bb:
        im = im.crop(bb)
    k = fill * size / max(im.size)
    im = im.resize((max(1, int(im.width * k)), max(1, int(im.height * k))), Image.LANCZOS)
    bg = Image.new("RGBA", (size, size), "white")
    bg.alpha_composite(im, ((size - im.width) // 2, (size - im.height) // 2))
    return bg.convert("RGB")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--views", required=True)
    ap.add_argument("--face")
    ap.add_argument("--out", required=True)
    ap.add_argument("--size", type=int, default=1024)
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    names = []
    for n in ("front", "three-quarter", "side", "back"):
        p = os.path.join(a.views, f"view-{n}.png")
        if os.path.exists(p):
            square(Image.open(p), a.size).save(os.path.join(a.out, f"{n}.png"))
            names.append(n)
    if a.face:
        square(Image.open(a.face), a.size, 0.9).save(os.path.join(a.out, "face.png"))
        names.append("face")
    t = 300
    sheet = Image.new("RGB", (t * len(names), t), "white")
    for i, n in enumerate(names):
        sheet.paste(Image.open(os.path.join(a.out, f"{n}.png")).resize((t, t)), (i * t, 0))
    sheet.save(os.path.join(a.out, "_sheet.png"))
    print("prepared:", ", ".join(names), "->", a.out)


if __name__ == "__main__":
    main()
