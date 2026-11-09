// Builds the Kumo character model sheet from the reference-derived assets.
// Run `python3 prep.py` first (writes ../assets), then:  node build.mjs
// Writes ../kumo-model-sheet.svg (references ./assets/*.png) and
// ../expressions/kumo-<name>.svg.
import fs from 'node:fs';
import path from 'node:path';

const ROOT = path.resolve(path.dirname(new URL(import.meta.url).pathname), '..');
const W = 2400;
const H = 1900;
const BG = '#F5F5F3';
const PANEL = '#FFFFFF';
const RULE = '#E2E1DD';
const TXT = '#2E2A27';
const MUTED = '#8A8580';
const ACC = '#5B3A2E';
const SANS = "Inter, 'Helvetica Neue', Arial, sans-serif";
const MONO = "'JetBrains Mono', 'DejaVu Sans Mono', monospace";

const size = (f) => {
  const b = fs.readFileSync(path.join(ROOT, 'assets', f));
  return [b.readUInt32BE(16), b.readUInt32BE(20)];
};
const img = (f, x, y, s, extra = '') => {
  const [w, h] = size(f);
  return `<image href="assets/${f}" x="${x}" y="${y}" width="${w * s}" height="${h * s}" ${extra}/>`;
};
const t = (x, y, s, o = {}) => {
  const { size: fs_ = 14, weight = 500, fill = TXT, anchor = 'start', font = SANS, ls = 0 } = o;
  return `<text x="${x}" y="${y}" font-family="${font}" font-size="${fs_}" font-weight="${weight}" fill="${fill}" text-anchor="${anchor}" letter-spacing="${ls}">${s}</text>`;
};
const rect = (x, y, w, h) => `<rect x="${x}" y="${y}" width="${w}" height="${h}" rx="12" fill="${PANEL}" stroke="${RULE}" stroke-width="1.5"/>`;
const ln = (x1, y1, x2, y2, o = {}) =>
  `<line x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}" stroke="${o.c ?? RULE}" stroke-width="${o.w ?? 1.2}" ${o.dash ? `stroke-dasharray="${o.dash}"` : ''} stroke-linecap="round"/>`;
const head = (x, y, n, title, sub = '') =>
  `<circle cx="${x + 26}" cy="${y + 30}" r="15" fill="${ACC}"/>` +
  t(x + 26, y + 35.5, n, { size: 15, weight: 700, fill: '#fff', anchor: 'middle' }) +
  t(x + 52, y + 36, title, { size: 19, weight: 700, ls: 1.6 }) +
  (sub ? t(x + 52 + title.length * 15.6 + 14, y + 36, sub, { size: 13, fill: MUTED, ls: 0.4 }) : '');
const caption = (cx, y, a, b) => t(cx, y, a, { size: 13, weight: 700, anchor: 'middle', ls: 1 }) + (b ? t(cx, y + 18, b, { size: 11, fill: MUTED, anchor: 'middle', font: MONO }) : '');
const dim = (x, y1, y2, lab, val, side = 'end') => {
  const dx = side === 'end' ? -10 : 10;
  return ln(x, y1, x, y2, { c: ACC, w: 1.4 }) + ln(x - 6, y1, x + 6, y1, { c: ACC, w: 1.4 }) + ln(x - 6, y2, x + 6, y2, { c: ACC, w: 1.4 }) +
    t(x + dx, (y1 + y2) / 2 - 2, lab, { size: 11, weight: 700, fill: ACC, anchor: side, ls: 1 }) +
    t(x + dx, (y1 + y2) / 2 + 13, val, { size: 11, weight: 600, fill: MUTED, anchor: side, font: MONO });
};

/* ---------------------------------------------------------------- measured proportions
   Measured on the reference front view (assets/view-front.png, 3x scale):
   crest tip y=33, eye line y=315, chin y=465, crotch y=720, ground y=880.
   Head width x 18..490. 1 H = head height = 432 px. */
const M = { crest: 33, eye: 315, chin: 465, hip: 720, ground: 880, Hpx: 432 };
const hu = (px) => (px / M.Hpx).toFixed(2);

/* ---------------------------------------------------------------- expressions
   Overlays drawn on the reference face (assets/face-front.png), in face-crop
   pixel units (152 x 136; the asset is that crop at 4x). Measured anchors: */
const EYE = { L: { c: [35, 87], p: [43.5, 88] }, R: { c: [114.5, 87], p: [106, 88] } };
const COL = { line: '#2F1606', mouth: '#5A2A1C', tongue: '#D9826F', lidA: '#5BAE5E', lidB: '#3C8F4C', brow: '#3A8F48', skin: '#A3C64E' };
const EX = {
  neutral: { name: 'NEUTRAL / OBSERVANT', note: 'reference face, unchanged' },
  curious: { name: 'CURIOUS', note: 'one brow up · gaze up-right', po: [3, -4], brow: { L: [-9, -6], R: [-1, 0] }, mouth: 'M40 115.5 Q72 120 110 112.5' },
  surprised: { name: 'SURPRISED', note: 'brows high · pupils shrink', po: [0, 0], ps: 0.62, brow: { L: [-10, -8], R: [-10, -8] }, mouth: 'o' },
  happy: { name: 'HAPPY', note: 'lower lids up · open smile', lid: { L: [0, 0.32], R: [0, 0.32] }, brow: { L: [-5, -4], R: [-5, -4] }, mouth: 'smile' },
  confused: { name: 'CONFUSED', note: 'uneven brows · wavy mouth', po: [-3, -3], lid: { L: [0, 0], R: [0.3, 0] }, brow: { L: [-10, -5], R: [3, 3] }, mouth: 'M42 116 C55 111 62 121 75 116 S96 111 108 118' },
  suspicious: { name: 'SUSPICIOUS', note: 'heavy lids · side glance', po: [6, 1], lid: { L: [0.46, 0.12], R: [0.46, 0.12] }, tilt: 3, brow: { L: [5, -1], R: [5, -1] }, mouth: 'M44 117 Q80 118 110 110.5' },
  excited: { name: 'EXCITED', note: 'big pupils · brows up · grin', ps: 1.18, sparkle: true, brow: { L: [-10, -10], R: [-10, -10] }, mouth: 'grin' },
  thoughtful: { name: 'THOUGHTFUL', note: 'half lids · gaze up-left', po: [-4, -6], lid: { L: [0.3, 0], R: [0.3, 0] }, brow: { L: [-7, -2], R: [1, 1] }, mouth: 'M80 116.5 Q90 113.5 101 116.5' },
};

let uid = 0;
function eyeOverlay(side, e) {
  const { c, p } = EYE[side];
  const [cx, cy] = c;
  const s = side === 'L' ? -1 : 1; // -1 = viewer-left eye
  let out = '';
  const cid = `ec${++uid}`;
  out += `<clipPath id="${cid}"><ellipse cx="${cx}" cy="${cy}" rx="18.6" ry="25.4"/></clipPath><g clip-path="url(#${cid})">`;
  if (e.po || e.ps || e.sparkle) {
    const po = e.po || [0, 0];
    const ps = e.ps || 1;
    const px = p[0] + po[0];
    const py = p[1] + po[1];
    out += `<ellipse cx="${cx}" cy="${cy}" rx="18.6" ry="25.4" fill="url(#iris${side})"/>`;
    out += `<ellipse cx="${px}" cy="${py}" rx="${10.6 * ps}" ry="${19 * ps}" fill="#F4AE22"/>`;
    out += `<ellipse cx="${px}" cy="${py}" rx="${9.3 * ps}" ry="${17.6 * ps}" fill="#0E0A06"/>`;
    out += `<circle cx="${px + 4.6 * ps}" cy="${py - 9 * ps}" r="${2.6 * Math.max(ps, 0.8)}" fill="#fff"/>`;
    if (e.sparkle) out += `<circle cx="${px - 3.5}" cy="${py + 8}" r="1.3" fill="#fff"/><circle cx="${px + 1}" cy="${py - 13}" r="1" fill="#fff"/>`;
  }
  const lid = e.lid?.[side];
  if (lid && lid[0] > 0) {
    const top = cy - 25.4;
    const y = top + 50.8 * lid[0];
    const ti = (e.tilt || 0) * -s; // lower toward the nose
    const xin = cx - 20 * s, xout = cx + 20 * s;
    out += `<path d="M${cx - 21} ${top - 2} L${cx + 21} ${top - 2} L${xin > xout ? xin : xout} ${y + (xin > xout ? ti : -ti)} Q${cx} ${y + 3} ${xin > xout ? xout : xin} ${y + (xin > xout ? -ti : ti)} Z" fill="url(#lid)"/>`;
    out += `<path d="M${Math.min(xin, xout)} ${y + (xin > xout ? -ti : ti)} Q${cx} ${y + 3} ${Math.max(xin, xout)} ${y + (xin > xout ? ti : -ti)}" fill="none" stroke="${COL.line}" stroke-width="1.6"/>`;
  }
  if (lid && lid[1] > 0) {
    const bot = cy + 25.4;
    const y = bot - 50.8 * lid[1];
    out += `<path d="M${cx - 21} ${bot + 2} L${cx + 21} ${bot + 2} L${cx + 21} ${y + 3} Q${cx} ${y - 5} ${cx - 21} ${y + 3} Z" fill="url(#lid)"/>`;
    out += `<path d="M${cx - 21} ${y + 3} Q${cx} ${y - 5} ${cx + 21} ${y + 3}" fill="none" stroke="${COL.line}" stroke-width="1.6"/>`;
  }
  out += '</g>';
  const b = e.brow?.[side];
  if (b) {
    const xi = cx - 14 * s, xo = cx + 17 * s;
    const yi = 61 + b[0], yo = 59 + b[1];
    const d = `M${xi} ${yi} Q${(xi + xo) / 2} ${(yi + yo) / 2 - 4} ${xo} ${yo}`;
    out += `<path d="${d}" fill="none" stroke="${COL.line}" stroke-width="5" stroke-linecap="round"/><path d="${d}" fill="none" stroke="${COL.brow}" stroke-width="2.8" stroke-linecap="round"/>`;
  }
  return out;
}
function mouthOverlay(m) {
  if (!m) return '';
  // soften the original mouth line before drawing the new one
  let out = `<g filter="url(#soft)"><path d="M33 111 Q75 108 117 111 L117 121 Q75 124 33 121 Z" fill="${COL.skin}" opacity="0.92"/></g>`;
  if (m === 'o') return out + `<ellipse cx="75" cy="118" rx="6" ry="7" fill="${COL.mouth}" stroke="${COL.line}" stroke-width="1.6"/>`;
  if (m === 'smile' || m === 'grin') {
    const d = m === 'smile' ? 'M40 113 Q75 116 110 113 Q75 134 40 113 Z' : 'M36 111 Q75 113 114 111 Q75 140 36 111 Z';
    const id = `m${++uid}`;
    return out + `<clipPath id="${id}"><path d="${d}"/></clipPath><path d="${d}" fill="${COL.mouth}"/><ellipse cx="75" cy="${m === 'smile' ? 127 : 131}" rx="${m === 'smile' ? 12 : 15}" ry="6" fill="${COL.tongue}" clip-path="url(#${id})"/><path d="${d}" fill="none" stroke="${COL.line}" stroke-width="1.7" stroke-linejoin="round"/>`;
  }
  return out + `<path d="${m}" fill="none" stroke="${COL.line}" stroke-width="1.7" stroke-linecap="round"/>`;
}
const exprDefs = `
<radialGradient id="irisL" cx="0.62" cy="0.5" r="0.62"><stop offset="0.55" stop-color="#F9D993"/><stop offset="0.86" stop-color="#F2B24A"/><stop offset="1" stop-color="#DE9728"/></radialGradient>
<radialGradient id="irisR" cx="0.38" cy="0.5" r="0.62"><stop offset="0.55" stop-color="#F9D993"/><stop offset="0.86" stop-color="#F2B24A"/><stop offset="1" stop-color="#DE9728"/></radialGradient>
<linearGradient id="lid" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="${COL.lidB}"/><stop offset="1" stop-color="${COL.lidA}"/></linearGradient>
<filter id="soft" x="-10%" y="-50%" width="120%" height="200%"><feGaussianBlur stdDeviation="1.4"/></filter>`;
const face = (key, href = 'assets/face-front.png') => {
  const e = EX[key];
  return `<image href="${href}" x="0" y="0" width="152" height="136"/>` + eyeOverlay('L', e) + eyeOverlay('R', e) + mouthOverlay(e.mouth);
};

let svg = '';

/* ---------------------------------------------------------------- header */
svg += t(48, 92, 'KUMO', { size: 64, weight: 800, fill: ACC, ls: 4 });
svg += ln(268, 44, 268, 104, { w: 2 });
svg += t(292, 70, 'CHARACTER MODEL SHEET', { size: 24, weight: 700, ls: 2.4 });
svg += t(292, 98, 'Official design reference · turnaround · proportions · expressions · construction · identity', { size: 14.5, fill: MUTED, ls: 0.3 });
let tx = 2352;
for (const tag of ['CHAMELEON', 'ANTHROPOMORPHIC', 'BIPEDAL', 'NO CLOTHING', 'NO ACCESSORIES'].reverse()) {
  const w = tag.length * 9.4 + 28;
  tx -= w;
  svg += `<rect x="${tx}" y="50" width="${w}" height="30" rx="15" fill="none" stroke="${RULE}" stroke-width="1.5"/>` + t(tx + w / 2, 70, tag, { size: 12, weight: 600, anchor: 'middle', ls: 1.2 });
  tx -= 10;
}
svg += t(2352, 104, 'SHEET KUMO-MS-01 · v2.0 · ART FROM THE APPROVED REFERENCE · 1 H = HEAD HEIGHT', { size: 11.5, fill: MUTED, anchor: 'end', font: MONO, ls: 0.5 });

/* ---------------------------------------------------------------- 1. turnaround */
{
  const X = 40, Y = 130, Wp = 1560, Hp = 690;
  svg += rect(X, Y, Wp, Hp) + head(X, Y, '1', 'TURNAROUND', '· orthographic · same scale and ground line in every view');
  const s = 0.56;
  const ground = Y + Hp - 92;
  const top = ground - M.ground * s; // image top
  const guides = [
    [M.ground, '0'],
    [M.hip, `${hu(M.ground - M.hip)} H`],
    [M.chin, `${hu(M.ground - M.chin)} H`],
    [M.crest, `${hu(M.ground - M.crest)} H`],
  ];
  for (const [y, lab] of guides) {
    const yy = top + y * s;
    svg += ln(X + 96, yy, X + Wp - 28, yy, { c: y === M.ground ? '#BDB8B1' : RULE, w: y === M.ground ? 1.6 : 1.1, dash: y === M.ground ? '' : '6 6' });
    svg += t(X + 84, yy + 4.5, lab, { size: 12, weight: 600, anchor: 'end', font: MONO, fill: MUTED });
  }
  const bx = X + 28;
  const br = (a, b, lab) => {
    const y1 = top + a * s, y2 = top + b * s;
    return ln(bx, y1 + 3, bx, y2 - 3, { c: ACC, w: 1.4 }) + ln(bx - 5, y1 + 3, bx + 5, y1 + 3, { c: ACC, w: 1.4 }) + ln(bx - 5, y2 - 3, bx + 5, y2 - 3, { c: ACC, w: 1.4 }) +
      `<text transform="translate(${bx - 9} ${(y1 + y2) / 2}) rotate(-90)" font-family="${SANS}" font-size="11" font-weight="700" fill="${ACC}" text-anchor="middle" letter-spacing="1.2">${lab}</text>`;
  };
  svg += br(M.crest, M.chin, 'HEAD') + br(M.chin, M.hip, 'TORSO') + br(M.hip, M.ground, 'LEGS');
  const views = [['view-front.png', 'FRONT VIEW', '0°'], ['view-three-quarter.png', '3/4 VIEW', '45°'], ['view-side.png', 'SIDE VIEW', '90°'], ['view-back.png', 'BACK VIEW', '180°']];
  // place views left to right with equal gaps (tails point different ways per view)
  const widths = views.map(([f]) => size(f)[0] * s);
  const gap = (Wp - 150 - widths.reduce((a, b) => a + b, 0)) / 3;
  let vx = X + 120;
  views.forEach(([f, name, deg], i) => {
    const cx = vx + widths[i] / 2;
    svg += img(f, vx, top, s);
    vx += widths[i] + gap;
    svg += t(cx, ground + 44, name, { size: 15, weight: 700, anchor: 'middle', ls: 1.6 });
    svg += t(cx, ground + 64, `rotation ${deg}`, { size: 11.5, anchor: 'middle', fill: MUTED, font: MONO });
  });
}

/* ---------------------------------------------------------------- 2. proportions */
{
  const X = 1630, Y = 130, Wp = 730, Hp = 690;
  svg += rect(X, Y, Wp, Hp) + head(X, Y, '2', 'PROPORTIONS', '· measured on the reference');
  const s = 0.6;
  const ground = Y + Hp - 70;
  const top = ground - M.ground * s;
  const ix = X + 110;
  for (const y of [M.crest, M.eye, M.chin, M.hip, M.ground]) svg += ln(X + 96, top + y * s, X + 470, top + y * s, { c: '#E9E7E3', w: 1 });
  svg += img('view-front.png', ix, top, s);
  const dx = X + 90;
  svg += dim(dx, top + M.crest * s, top + M.chin * s, 'HEAD', '1.00 H') + dim(dx, top + M.chin * s, top + M.hip * s, 'TORSO', `${hu(M.hip - M.chin)} H`) + dim(dx, top + M.hip * s, top + M.ground * s, 'LEGS', `${hu(M.ground - M.hip)} H`);
  const hy = top + 12;
  const x1 = ix + 18 * s, x2 = ix + 490 * s;
  svg += ln(x1, hy, x2, hy, { c: ACC, w: 1.4 }) + ln(x1, hy - 6, x1, hy + 6, { c: ACC, w: 1.4 }) + ln(x2, hy - 6, x2, hy + 6, { c: ACC, w: 1.4 });
  svg += t((x1 + x2) / 2, hy - 10, `HEAD WIDTH ${hu(490 - 18)} H`, { size: 11, weight: 700, fill: ACC, anchor: 'middle', ls: 1 });
  const rows = [
    ['Total height', `${hu(M.ground - M.crest)} H`],
    ['Head (crest tip → chin)', '1.00 H'],
    ['Head width', `${hu(490 - 18)} H`],
    ['Torso, no visible neck', `${hu(M.hip - M.chin)} H`],
    ['Legs incl. feet', `${hu(M.ground - M.hip)} H`],
    ['Eye width / head width', '29 %'],
    ['Pupil / iris', '45 %'],
    ['Tail spiral diameter', `${hu(610 - 420)} H`],
    ['Tail spiral', '≈ 1.5–2 turns'],
    ['Fingers / toes', '3 + thumb / 3'],
  ];
  const tx0 = X + 480, ty0 = Y + 96;
  svg += t(tx0, ty0, 'MEASURES', { size: 12, weight: 700, ls: 1.6, fill: MUTED });
  rows.forEach(([k, v], i) => {
    const y = ty0 + 36 + i * 44;
    svg += t(tx0, y, k, { size: 12.5 }) + t(X + Wp - 24, y, v, { size: 13, weight: 700, anchor: 'end', font: MONO, fill: ACC });
    svg += ln(tx0, y + 25, X + Wp - 24, y + 25, { c: '#EFEDE9', w: 1 });
  });
  svg += t(tx0, ty0 + 34 + rows.length * 44 + 10, 'Head ≈ 51 % of total height.', { size: 12, fill: MUTED });
}

/* ---------------------------------------------------------------- 3. expressions */
{
  const X = 40, Y = 845, Wp = 2320, Hp = 350;
  svg += rect(X, Y, Wp, Hp) + head(X, Y, '3', 'FACIAL EXPRESSIONS', '· eyes, lids, brow ridges and mouth only · the faceted head never changes');
  const keys = Object.keys(EX);
  const sw = (Wp - 40) / 8;
  const k = 1.5;
  keys.forEach((key, i) => {
    const cx = X + 20 + sw * i + sw / 2;
    if (i) svg += ln(X + 20 + sw * i, Y + 80, X + 20 + sw * i, Y + Hp - 26, { c: '#EFEDE9', w: 1.2 });
    svg += `<g transform="translate(${cx - 76 * k} ${Y + 72}) scale(${k})">${face(key)}</g>`;
    svg += caption(cx, Y + Hp - 48, `${String(i + 1).padStart(2, '0')} · ${EX[key].name}`, EX[key].note);
  });
}

/* ---------------------------------------------------------------- 4. anatomy */
{
  const X = 40, Y = 1220, Wp = 2320, Hp = 345;
  svg += rect(X, Y, Wp, Hp) + head(X, Y, '4', 'ANATOMICAL CONSTRUCTION');
  const sep = (x) => ln(x, Y + 70, x, Y + Hp - 22, { c: '#EFEDE9', w: 1.2 });
  // construction strip (reference pencil construction, 6 steps)
  const s = 0.5;
  const sx = X + 26, sy = Y + 66;
  svg += img('sketch-construction.png', sx, sy, s);
  const steps = [
    [80, '1 · POLYGONAL HEAD', '12–16 faces'],
    [218, '2 · GUIDES', 'axis · eyes · snout'],
    [369, '3 · SNOUT &amp; JAW', 'simple facets'],
    [530, '4 · PRIMITIVES', 'ovoid · cylinders'],
    [691, '5 · VOLUME', 'chest · hips'],
    [857, '6 · FINAL', 'eyes · crest'],
  ];
  for (const [x, a, b] of steps) svg += caption(sx + (x - 18) * 2 * s, Y + Hp - 50, a, b);
  svg += sep(X + 970);
  const tile = (cx, f, sc, cyTop, a, b) => {
    const [w, h] = size(f);
    return img(f, cx - (w * sc) / 2, cyTop + (215 - h * sc) / 2, sc) + caption(cx, Y + Hp - 50, a, b);
  };
  let cx = X + 1075;
  svg += tile(cx, 'detail-eye.png', 0.62, Y + 64, 'EYE', 'amber iris · pupil 45%');
  svg += sep(cx + 105);
  cx += 205;
  svg += tile(cx, 'detail-hand.png', 0.66, Y + 64, 'HAND', '3 fingers + thumb');
  svg += sep(cx + 100);
  cx += 195;
  svg += tile(cx, 'detail-foot.png', 0.66, Y + 64, 'FOOT', '3 forward toes');
  svg += sep(cx + 100);
  cx += 230;
  svg += img('sketch-tail-side.png', cx - 150, Y + 92, 0.85) + img('sketch-tail-back.png', cx + 10, Y + 80, 0.85);
  svg += caption(cx, Y + Hp - 50, 'TAIL SPIRAL', 'long · flexible · spiral tip');
  svg += sep(cx + 165);
  cx += 300;
  // crest → dorsal line: upper back view
  svg += `<clipPath id="crestclip"><rect x="${cx - 130}" y="${Y + 66}" width="260" height="215"/></clipPath>`;
  svg += `<g clip-path="url(#crestclip)">${img('view-back.png', cx - (489 * 0.4) / 2, Y + 60, 0.4)}</g>`;
  svg += caption(cx, Y + Hp - 50, 'CREST → DORSAL LINE', 'triangular, head to tail');
}

/* ---------------------------------------------------------------- 5. identity */
{
  const X = 40, Y = 1590, Wp = 2320, Hp = 270;
  svg += rect(X, Y, Wp, Hp) + head(X, Y, '5', 'VISUAL IDENTITY', '· palette from the approved reference');
  const pal = [
    ['#1B5E3B', 'dark green', 'Head top · crest · dorsal'],
    ['#4CAF6B', 'mid green', 'Body · torso · limbs'],
    ['#C9D45B', 'yellow-green', 'Organic camouflage spots'],
    ['#EAD9B7', 'light beige', 'Belly · ventral area'],
    ['#F4B642', 'golden amber', 'Iris · black pupil'],
    ['#5B3A2E', 'dark brown', 'Outlines · detail lines'],
  ];
  pal.forEach(([hex, nm, role], i) => {
    const x = X + 34 + i * 215;
    const y = Y + 82;
    svg += `<circle cx="${x + 34}" cy="${y + 34}" r="32" fill="${hex}" stroke="${RULE}" stroke-width="1.5"/>`;
    svg += t(x + 78, y + 28, hex, { size: 13, weight: 700, font: MONO, fill: ACC }) + t(x + 78, y + 46, nm, { size: 12, fill: MUTED });
    svg += t(x, y + 100, role, { size: 12.5, weight: 600 });
  });
  const nx = X + 1360;
  svg += ln(nx - 24, Y + 76, nx - 24, Y + Hp - 24, { c: '#EFEDE9', w: 1.2 });
  svg += t(nx, Y + 92, 'STYLE', { size: 12, weight: 700, fill: MUTED, ls: 1.6 });
  ['Stylized 3D cartoon render', 'Geometric, angular, slightly squared', 'Polyhedral head, no soft round surfaces', 'Dark brown outlines, flat even lighting', 'Subtle scale texture, simple silhouette']
    .forEach((s, i) => (svg += t(nx, Y + 118 + i * 24, '· ' + s, { size: 13 })));
  const rx = X + 1860;
  svg += ln(rx - 24, Y + 76, rx - 24, Y + Hp - 24, { c: '#EFEDE9', w: 1.2 });
  svg += t(rx, Y + 92, 'NEVER', { size: 12, weight: 700, fill: '#B5452F', ls: 1.6 });
  ['Clothing, shoes or backpacks', 'Accessories or held objects', 'Other finger or toe counts', 'Colour or proportion changes', 'Alternative versions of Kumo']
    .forEach((s, i) => (svg += t(rx, Y + 118 + i * 24, '✕ ' + s, { size: 13 })));
}

svg += t(48, H - 14, 'Character art: approved Kumo reference renders (referencia de modelo/). Every illustration, animation and 3D model must match this sheet.', { size: 11, fill: MUTED, font: MONO });

const doc = `<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="${W}" height="${H}" viewBox="0 0 ${W} ${H}">
<title>Kumo — Character Model Sheet</title>
<defs>${exprDefs}</defs>
<rect width="${W}" height="${H}" fill="${BG}"/>
${svg}
</svg>`;
fs.writeFileSync(path.join(ROOT, 'kumo-model-sheet.svg'), doc);

// individual expressions
fs.mkdirSync(path.join(ROOT, 'expressions'), { recursive: true });
for (const key of Object.keys(EX)) {
  fs.writeFileSync(
    path.join(ROOT, 'expressions', `kumo-${key}.svg`),
    `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 152 136" width="608" height="544"><defs>${exprDefs}</defs>${face(key, '../assets/face-front.png')}</svg>`,
  );
}
console.log('built');
