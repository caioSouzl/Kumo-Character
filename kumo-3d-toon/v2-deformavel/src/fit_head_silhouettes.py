"""P3 — fit the named head control vertices to the reference silhouettes (4 views).

    python3 fit_head_silhouettes.py --out p3/head_verts_p3.json [--rodin p3/rodin_head_verts.json]

The approved head is the convex hull of HEAD_VERTS (mirrored across X). Under an
orthographic camera the silhouette of a convex hull is the convex hull of the projected
vertices, so each view can be evaluated exactly and fast without rendering.

Objective: mean head IoU (rows above the chin, z >= 0.95 H) against the reference cut-outs
character-model-sheet/assets/view-{front,three-quarter,side,back}.png, with the same
alignment as tools/kumo_silhouette.py (ground line, centre of the widest head row).
Cameras: front 0, three-quarter -40 (approved P8), side -90, back 180.

Constraints (approved P1/P2 proportions): crest tip T keeps z = 1.965; chin plate J, K keeps
z = 0.955; vertices on the centre line keep x = 0; every coordinate moves at most MAX_MOVE
from the approved value; a small penalty keeps moves minimal. The front-view width of the
skull (D) is free but starts at the approved value, which already matches reference 01.
"""
import argparse
import json
import math
import os
import sys

from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "kumo-3d-toon", "tools"))
import kumo_silhouette as ks  # noqa: E402

# approved P1/P2 head (copy of kumo_common.HEAD_VERTS, which needs bpy to import)
P1 = {
    "T": (0.0, 0.02, 1.965), "S": (0.21, -0.21, 1.79), "V": (0.0, -0.50, 1.53),
    "Q": (0.13, 0.49, 1.62), "Bt": (0.0, 0.66, 1.24),
    "A": (0.50, -0.45, 1.57), "B": (0.47, 0.51, 1.55),
    "D": (0.555, -0.43, 1.24), "E": (0.555, 0.60, 1.30),
    "F": (0.47, -0.34, 1.04), "G": (0.44, 0.53, 1.04),
    "J": (0.23, -0.17, 0.955), "K": (0.22, 0.36, 0.955),
    "N": (0.0, -0.565, 1.20), "L": (0.0, -0.50, 1.09),
}
VIEWS = {"front": 0, "three-quarter": -40, "side": -90, "back": 180}
FIXED_Z = {"T", "J", "K"}
MAX_MOVE = 0.12
PENALTY = 0.6
S = ks.S
CHIN_ROWS = round(0.95 * S)


def load_refs():
    refs = {}
    for v in VIEWS:
        m = ks.normalise(ks.mask(Image.open(os.path.join(ROOT, "character-model-sheet", "assets", f"view-{v}.png"))), ks.REF["ground"], ks.REF["H"])
        refs[v] = m
    return refs


def all_points(hv):
    pts = []
    for (x, y, z) in hv.values():
        pts.append((x, y, z))
        if abs(x) > 1e-9:
            pts.append((-x, y, z))
    return pts


def hull2d(p):
    p = sorted(set(p))
    if len(p) < 3:
        return p
    cross = lambda o, a, b: (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lo, up = [], []
    for q in p:
        while len(lo) >= 2 and cross(lo[-2], lo[-1], q) <= 0:
            lo.pop()
        lo.append(q)
    for q in reversed(p):
        while len(up) >= 2 and cross(up[-2], up[-1], q) <= 0:
            up.pop()
        up.append(q)
    return lo[:-1] + up[:-1]


def silhouette(hv, az):
    a = math.radians(az)
    rx, ry = math.cos(a), math.sin(a)
    W, Hc = round(3.2 * S), round(2.6 * S)
    ground = Hc - 1
    proj = [(W / 2 + (x * rx + y * ry) * S, ground - z * S) for x, y, z in all_points(hv)]
    img = Image.new("L", (W, Hc), 0)
    ImageDraw.Draw(img).polygon(hull2d(proj), fill=255)
    rgba = Image.merge("RGBA", (img, img, img, img))
    return ks.normalise(ks.mask(rgba), ground, S)


def head_iou(m, ref):
    h = min(m.height, ref.height)
    a = ref.crop((0, 0, ref.width, h)).load()
    b = m.crop((0, 0, m.width, h)).load()
    i = u = 0
    for y in range(0, h - CHIN_ROWS, 2):
        for x in range(0, ref.width, 2):
            p, q = a[x, y] > 0, b[x, y] > 0
            i += p and q
            u += p or q
    return i / u if u else 0.0


def scores(hv, refs):
    return {v: head_iou(silhouette(hv, az), refs[v]) for v, az in VIEWS.items()}


def objective(hv, refs):
    sc = scores(hv, refs)
    move = sum((a - b) ** 2 for k in hv for a, b in zip(hv[k], P1[k])) / len(hv)
    return sum(sc.values()) / len(sc) - PENALTY * move, sc


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--rounds", type=int, default=6)
    a = ap.parse_args()
    refs = load_refs()
    hv = {k: list(v) for k, v in P1.items()}
    best, sc0 = objective(hv, refs)
    print("P1 head IoU:", {k: round(v, 4) for k, v in sc0.items()}, "objective", round(best, 4))
    for step in (0.04, 0.02, 0.01, 0.005):
        for _ in range(a.rounds):
            improved = False
            for k in hv:
                for axis in range(3):
                    if axis == 0 and abs(P1[k][0]) < 1e-9:
                        continue
                    if axis == 2 and k in FIXED_Z:
                        continue
                    for d in (step, -step):
                        trial = {kk: list(vv) for kk, vv in hv.items()}
                        trial[k][axis] += d
                        if abs(trial[k][axis] - P1[k][axis]) > MAX_MOVE:
                            continue
                        val, _ = objective(trial, refs)
                        if val > best + 1e-5:
                            hv, best, improved = trial, val, True
                            break
            if not improved:
                break
        print(f"step {step}: objective {best:.4f}")
    final, scf = objective(hv, refs)
    out = dict(head_verts={k: [round(c, 4) for c in v] for k, v in hv.items()},
               iou_head_p1=sc0, iou_head_p3=scf,
               delta={k: [round(a - b, 4) for a, b in zip(hv[k], P1[k])] for k in hv},
               method="coordinate descent on convex-hull silhouettes vs reference 01 cut-outs",
               constraints=dict(fixed_z=sorted(FIXED_Z), max_move=MAX_MOVE, penalty=PENALTY))
    with open(a.out, "w") as fh:
        json.dump(out, fh, indent=1)
    print("P3 head IoU:", {k: round(v, 4) for k, v in scf.items()})
    for k in hv:
        print(f"{k:3s} {P1[k]} -> {tuple(round(c, 3) for c in hv[k])}")


if __name__ == "__main__":
    main()
