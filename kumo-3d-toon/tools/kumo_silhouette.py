"""kumo-silhouette — compare orthographic render silhouettes with the reference cut-outs.

    python3 kumo_silhouette.py --renders ../renders --ref ../../character-model-sheet/assets --out ../docs/inspecao

Both images are brought to head-height units (1 H) and aligned on the ground line and on
the centre of the head's widest row. Output, per view (front / three-quarter / side / back):
  - IoU (intersection over union) of the two silhouettes,
  - a width profile: left and right edge of each silhouette every 0.05 H, and the gap in H,
  - an overlay PNG: reference in red, model in blue, overlap in dark grey.
JSON to stdout, Markdown + overlays to --out. Read-only: never touches the model.
"""
import argparse
import json
import os

from PIL import Image

# reference cut-outs (character-model-sheet/assets/view-*.png): 3x scale of reference 01,
# ground at y = 880 px, 1 H = 432 px (measured: crest tip y = 33, chin y = 465)
REF = dict(ground=880, H=432)
# Blender renders (kumo_toon.py): ortho_scale 2.45 at R px, camera centred on z = 1.0
ORTHO, TARGET_Z = 2.45, 1.0
VIEWS = ["front", "three-quarter", "side", "back"]
S = 200  # working resolution: px per H


def mask(im, thr=128):
    return im.getchannel("A").point(lambda v: 255 if v >= thr else 0)


def normalise(m, ground, H):
    """Scale a mask so 1 H = S px and put the ground line at the bottom of a 2.3 H canvas."""
    k = S / H
    m = m.resize((max(1, round(m.width * k)), max(1, round(m.height * k))), Image.NEAREST)
    g = ground * k
    top = round(g - 2.3 * S)
    m = m.crop((0, top, m.width, top + round(2.3 * S)))
    # centre of the widest head row (z between 1.15 and 1.45 H)
    best = (0, 0, 0)
    for z in range(round(1.15 * S), round(1.45 * S)):
        y = m.height - z
        xs = [x for x in range(m.width) if m.getpixel((x, y))]
        if xs and xs[-1] - xs[0] > best[0]:
            best = (xs[-1] - xs[0], xs[0], xs[-1])
    cx = (best[1] + best[2]) / 2
    W = round(3.2 * S)
    out = Image.new("L", (W, m.height), 0)
    out.paste(m, (round(W / 2 - cx), 0))
    return out


def profile(m):
    rows = []
    for i in range(0, 41):
        z = i * 0.05
        y = m.height - 1 - round(z * S)
        if y < 0:
            break
        xs = [x for x in range(m.width) if m.getpixel((x, y))]
        rows.append((round(z, 2), (xs[0] - m.width / 2) / S if xs else None, (xs[-1] - m.width / 2) / S if xs else None))
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--renders", required=True)
    ap.add_argument("--ref", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    res = {}
    md = ["# Silhouette comparison — model vs reference", "",
          "Units: H (head height). Both silhouettes aligned on the ground line and on the centre of the head's widest row.",
          "Overlay: red = reference only, blue = model only, grey = both.", ""]
    for v in VIEWS:
        ref = Image.open(os.path.join(a.ref, f"view-{v}.png"))
        ren = Image.open(os.path.join(a.renders, f"view-{v}.png"))
        R = ren.height
        ppu = R / ORTHO
        rm = normalise(mask(ref), REF["ground"], REF["H"])
        mm = normalise(mask(ren), R / 2 + TARGET_Z * ppu, ppu)
        h = min(rm.height, mm.height)
        rm, mm = rm.crop((0, 0, rm.width, h)), mm.crop((0, 0, mm.width, h))
        inter = union = 0
        ov = Image.new("RGB", rm.size, "white")
        rp, mp, op = rm.load(), mm.load(), ov.load()
        for y in range(h):
            for x in range(rm.width):
                r_, m_ = rp[x, y] > 0, mp[x, y] > 0
                inter += r_ and m_
                union += r_ or m_
                if r_ and m_:
                    op[x, y] = (90, 90, 90)
                elif r_:
                    op[x, y] = (230, 60, 60)
                elif m_:
                    op[x, y] = (60, 110, 230)
        iou = inter / union if union else 0
        ov.save(os.path.join(a.out, f"overlay-{v}.png"))
        pr, pm = profile(rm), profile(mm)
        rows = []
        for (z, rl, rr), (_, ml, mr) in zip(pr, pm):
            rows.append(dict(z=z, ref=[rl, rr], model=[ml, mr],
                             d_left=None if rl is None or ml is None else round(ml - rl, 3),
                             d_right=None if rr is None or mr is None else round(mr - rr, 3)))
        res[v] = dict(iou=round(iou, 4), profile=rows)
        md += [f"## {v} — IoU {iou:.3f}", "", f"![overlay](overlay-{v}.png)", "",
               "| z (H) | ref left | ref right | model left | model right | Δ left | Δ right |", "|---|---|---|---|---|---|---|"]
        f = lambda x: "—" if x is None else f"{x:+.3f}"
        for r in rows:
            if r["ref"][0] is None and r["model"][0] is None:
                continue
            md.append(f"| {r['z']:.2f} | {f(r['ref'][0])} | {f(r['ref'][1])} | {f(r['model'][0])} | {f(r['model'][1])} | {f(r['d_left'])} | {f(r['d_right'])} |")
        md.append("")
    with open(os.path.join(a.out, "silhuetas.md"), "w") as fh:
        fh.write("\n".join(md))
    with open(os.path.join(a.out, "silhuetas.json"), "w") as fh:
        json.dump(res, fh, indent=1)
    print(json.dumps({v: res[v]["iou"] for v in res}))


if __name__ == "__main__":
    main()
