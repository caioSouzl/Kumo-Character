---
name: hyper3d-rodin
description: Generate, download and evaluate 3D models of a character (Kumo or any reference-driven asset) with the Hyper3D / Rodin CLI (`hyper3d`). Use when the user asks to "use the Hyper3D app", "generate in Rodin", turn reference images into a 3D model, fetch a Rodin generation by ID or QR link, rig a Rodin model, or compare a Rodin model with reference images. Spends the user's Hyper3D credits — always say what will run and its cost first.
allowed-tools: Bash, Read, Write
---

# Hyper3D / Rodin — reference images → 3D model → evaluation

Learned on the Kumo project (2026-11-09). Rodin output is a **3D reference / shrinkwrap target**, not a production mesh: it comes back triangulated, often non-manifold, as one fused mesh, without deformation loops. Production topology stays in `kumo-3d-toon/v2-deformavel/`.

## 0. Setup (once per machine/session)

```bash
npm view @hyper3d/cli name version repository.url   # verify: DeemosTech/hyper3d-cli (official)
npm install --global @hyper3d/cli
hyper3d auth status            # "Not authenticated" → next line
hyper3d auth login --no-browser   # run in background; show the user the URL + code; they approve in their browser
hyper3d auth status            # account + credit balance (Regular / Subscription)
```

Never log in for the user or reuse a code. The login grants access to their credits.

## 1. Prepare inputs (most important step)

Rodin's own guidance: **one clear subject per image**. Never send a multi-view model sheet as a single image.

```bash
python3 .claude/skills/hyper3d-rodin/scripts/prepare_views.py \
  --views character-model-sheet/assets --face character-model-sheet/assets/face-front.png --out /tmp/rodin_in
```

This produces up to 5 square 1024 px PNGs on white (front, three-quarter, side, back and an optional face close-up), cut from the transparent view cut-outs (`character-model-sheet/src/prep.py` produces them from the official references). Open the contact sheet and check it before submitting.

## 2. Generate (costs credits — confirm first)

```bash
hyper3d --output json generate \
  --image /tmp/rodin_in/front.png --image /tmp/rodin_in/three-quarter.png \
  --image /tmp/rodin_in/side.png --image /tmp/rodin_in/back.png --image /tmp/rodin_in/face.png \
  --tier Gen-2.5-Medium --mesh-mode Quad --format glb \
  --prompt "<short identity description: proportions, crest, eyes, fingers/toes, tail, palette, 'no clothing, no accessories, no base'>"
```

- Kumo run `fc410dfd-…` cost **0.5 credit** (Gen-2.5-Medium, Quad, 5 images, about 3 min).
- `agentic` (beta) is for procedural n-gon props such as furniture and robots. Organic characters go to `generate`.
- **Never resubmit automatically** on a timeout. Poll the returned `generation_id` instead.

## 3. Wait and download

```bash
for i in $(seq 1 20); do hyper3d --output json poll --timeout 45 <ID> | tee /tmp/p.json; grep -q '"completed"\|"failed"\|"unknown"' /tmp/p.json && break; done
python3 .claude/skills/hyper3d-rodin/scripts/fetch_result.py <ID> --out "referencia de modelo/externas/rodin-<ID8>"
```

- `result` returns temporary signed URLs. Download them straight away and never paste `files[].url` to the user.
- A QR code on a Rodin share card holds `https://hyper3d.ai/workspace/rodin/<generation_id>`. The ID works with `status`/`poll`. `result` can answer `INVALID_REQUEST` for some generations (seen on a BANG-stage job from another account context). In that case ask the user to download from the website.

## 4. Evaluate (always, before using it)

```bash
python3 .claude/skills/hyper3d-rodin/scripts/render_glb.py <model.glb> <out_dir>      # needs bpy (pip install bpy==5.2.3)
python3 kumo-3d-toon/tools/kumo_inspect.py <copy.blend|.glb-imported> ...              # topology report
```

`render_glb.py` imports the GLB and prints mesh stats (vertices, faces, face shapes, non-manifold edges). It renders orthographic front / 3/4 (40°) / side / back / opposite side with the **diffuse texture as emission**, because plain PBR renders come out almost black with no lights. It also writes a contact sheet.

Then compare silhouettes with the reference (`kumo-3d-toon/tools/kumo_silhouette.py` helpers, normalising by total height = 1.96 H) and write a `LEIAME.md` next to the files: ID, cost, inputs, mesh stats, IoU table, recommended use.

## 5. Optional: rigging and animation (costs credits)

```bash
hyper3d animation-presets                       # categories
hyper3d rigging <ID> --bone-template human --format fbx [--animation-preset <id> ...]
```

Use it only for previews. The production rig follows the project decisions: hybrid shape keys + bones (D4), A-pose rest pose (D3).

## Rules

- Say the exact command and expected cost before any `generate`, `agentic`, `bang` or `rigging` call.
- Store everything under `referencia de modelo/externas/` with a `LEIAME.md`. Never overwrite approved files.
- Rodin results never replace approved geometry directly. Present any divergence and ask for approval.
- Check terms of use before commercial use of generated assets.
