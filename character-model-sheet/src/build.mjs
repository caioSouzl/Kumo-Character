// Builds the Kumo character model sheet (SVG + HTML wrapper).
// Usage: node build.mjs <outDir>
import fs from 'node:fs';
import path from 'node:path';
import * as K from './kumo.mjs';

const out = process.argv[2] || path.resolve(path.dirname(new URL(import.meta.url).pathname), '..');
const W = 2400;
const Hh = 1600;
const BG = '#F6F6F4';
const PANEL = '#FFFFFF';
const RULE = '#E1E1DC';
const TXT = '#2E2A27';
const MUTED = '#8A8580';
const ACC = K.C.outline;
const SANS = "Inter, 'Helvetica Neue', Arial, sans-serif";
const MONO = "'JetBrains Mono', 'DejaVu Sans Mono', monospace";

const t = (x, y, s, o = {}) => {
  const { size = 14, weight = 500, fill = TXT, anchor = 'start', font = SANS, ls = 0, op = 1 } = o;
  return `<text x="${x}" y="${y}" font-family="${font}" font-size="${size}" font-weight="${weight}" fill="${fill}" text-anchor="${anchor}" letter-spacing="${ls}" opacity="${op}">${s}</text>`;
};
const rect = (x, y, w, h, o = {}) =>
  `<rect x="${x}" y="${y}" width="${w}" height="${h}" rx="${o.rx ?? 12}" fill="${o.fill ?? PANEL}" stroke="${o.stroke ?? RULE}" stroke-width="${o.sw ?? 1.5}"/>`;
const ln = (x1, y1, x2, y2, o = {}) =>
  `<line x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}" stroke="${o.c ?? RULE}" stroke-width="${o.w ?? 1.2}" ${o.dash ? `stroke-dasharray="${o.dash}"` : ''} stroke-linecap="round"/>`;
const g = (tx, ty, sc, body) => `<g transform="translate(${tx} ${ty}) scale(${sc})">${body}</g>`;
const dot = (x, y, r = 3.5, c = ACC) => `<circle cx="${x}" cy="${y}" r="${r}" fill="${c}"/>`;

function panelHead(x, y, n, title, sub = '') {
  return (
    `<circle cx="${x + 26}" cy="${y + 30}" r="15" fill="${ACC}"/>` +
    t(x + 26, y + 35.5, n, { size: 15, weight: 700, fill: '#fff', anchor: 'middle' }) +
    t(x + 52, y + 36, title, { size: 19, weight: 700, ls: 1.6 }) +
    (sub ? t(x + 52 + title.length * 15.6 + 14, y + 36, sub, { size: 13, weight: 500, fill: MUTED, ls: 0.6 }) : '')
  );
}
// callout: leader from (x1,y1) to (x2,y2) with label at x2
function callout(x1, y1, x2, y2, label, o = {}) {
  const anchor = o.anchor ?? (x2 >= x1 ? 'start' : 'end');
  const dx = anchor === 'start' ? 6 : -6;
  return (
    ln(x1, y1, x2, y2, { c: ACC, w: 1.1 }) + dot(x1, y1, 2.6) +
    t(x2 + dx, y2 + 4.5, label, { size: 12.5, weight: 600, anchor, font: SANS }) +
    (o.sub ? t(x2 + dx, y2 + 20, o.sub, { size: 11, weight: 500, fill: MUTED, anchor, font: MONO }) : '')
  );
}

let svg = '';

/* ---------------------------------------------------------------- header */
svg += t(48, 92, 'KUMO', { size: 64, weight: 800, fill: ACC, ls: 4 });
svg += ln(268, 44, 268, 104, { c: RULE, w: 2 });
svg += t(292, 70, 'CHARACTER MODEL SHEET', { size: 24, weight: 700, ls: 2.4 });
svg += t(292, 98, 'Official design reference · turnaround · expressions · construction · identity', { size: 14.5, weight: 500, fill: MUTED, ls: 0.4 });
const tags = ['CHAMELEON', 'ANTHROPOMORPHIC', 'BIPEDAL', 'NO CLOTHING', 'NO ACCESSORIES'];
let tx = 2352;
for (const tag of tags.slice().reverse()) {
  const w = tag.length * 9.4 + 28;
  tx -= w;
  svg += `<rect x="${tx}" y="50" width="${w}" height="30" rx="15" fill="none" stroke="${RULE}" stroke-width="1.5"/>`;
  svg += t(tx + w / 2, 70, tag, { size: 12, weight: 600, anchor: 'middle', ls: 1.2, fill: TXT });
  tx -= 10;
}
svg += t(2352, 104, 'SHEET KUMO-MS-01 · v1.0 · UNIT 1 H = HEAD HEIGHT', { size: 11.5, weight: 500, fill: MUTED, anchor: 'end', font: MONO, ls: 0.6 });

/* ---------------------------------------------------------------- 1. turnaround */
{
  const X = 40, Y = 130, Wp = 1560, Hp = 690;
  svg += rect(X, Y, Wp, Hp);
  svg += panelHead(X, Y, '1', 'TURNAROUND', '· orthographic, no perspective · identical scale in all views');
  const sc = 1.95;
  const ground = Y + Hp - 82;
  const levels = [
    [0, '0'],
    [60, '0.6 H'],
    [140, '1.4 H'],
    [240, '2.4 H'],
  ];
  const gx0 = X + 92;
  const gx1 = X + Wp - 28;
  for (const [v, lab] of levels) {
    const y = ground - v * sc;
    svg += ln(gx0, y, gx1, y, { c: v === 0 ? '#BDB8B1' : RULE, w: v === 0 ? 1.6 : 1.1, dash: v === 0 ? '' : '6 6' });
    svg += t(gx0 - 12, y + 4.5, lab, { size: 12, weight: 600, anchor: 'end', font: MONO, fill: MUTED });
  }
  // brackets on the left: head / torso / legs
  const bx = X + 30;
  const br = (a, b, lab) => {
    const y1 = ground - a * sc, y2 = ground - b * sc;
    return ln(bx, y1 + 3, bx, y2 - 3, { c: ACC, w: 1.4 }) + ln(bx - 5, y1 + 3, bx + 5, y1 + 3, { c: ACC, w: 1.4 }) + ln(bx - 5, y2 - 3, bx + 5, y2 - 3, { c: ACC, w: 1.4 }) +
      `<text transform="translate(${bx - 9} ${(y1 + y2) / 2}) rotate(-90)" font-family="${SANS}" font-size="11" font-weight="700" fill="${ACC}" text-anchor="middle" letter-spacing="1.2">${lab}</text>`;
  };
  svg += br(0, 60, 'LEGS') + br(60, 140, 'TORSO') + br(140, 240, 'HEAD');

  const slots = [
    ['FRONT VIEW', '0°', K.viewFront(), 33],
    ['3/4 VIEW', '45°', K.viewThreeQuarter(), 30],
    ['SIDE VIEW', '90°', K.viewSide(), -23],
    ['BACK VIEW', '180°', K.viewBack(), 33],
  ];
  const sx0 = X + 100;
  const sw = (Wp - 120) / 4;
  slots.forEach(([name, deg, body, mid], i) => {
    const cx = sx0 + sw * i + sw / 2;
    const ox = cx - mid * sc;
    svg += ln(ox, ground - 252 * sc, ox, ground + 8, { c: '#D8D3CC', w: 1, dash: '3 5' });
    svg += g(ox, ground, sc, body);
    svg += t(cx, ground + 44, name, { size: 15, weight: 700, anchor: 'middle', ls: 1.6 });
    svg += t(cx, ground + 64, `rotation ${deg}`, { size: 11.5, weight: 500, anchor: 'middle', fill: MUTED, font: MONO });
  });
}

/* ---------------------------------------------------------------- proportions */
{
  const X = 1630, Y = 130, Wp = 730, Hp = 690;
  svg += rect(X, Y, Wp, Hp);
  svg += panelHead(X, Y, '2', 'PROPORTIONS', '· official');
  const sc = 1.7;
  const ground = Y + Hp - 70;
  const cx = X + 200;
  const lev = (v) => ground - v * sc;
  // grid
  for (let v = 0; v <= 240; v += 20) svg += ln(X + 96, lev(v), cx + 228, lev(v), { c: v % 100 === 0 || v === 60 || v === 140 || v === 240 ? '#D5D0C9' : '#EFEDE9', w: 1 });
  svg += g(cx, ground, sc, `<g opacity="1">${K.viewFront()}</g>`);
  // vertical dimension chain on the left
  const dx = X + 92;
  const dim = (a, b, lab, val) => {
    const y1 = lev(a), y2 = lev(b);
    return ln(dx, y1, dx, y2, { c: ACC, w: 1.4 }) + ln(dx - 6, y1, dx + 6, y1, { c: ACC, w: 1.4 }) + ln(dx - 6, y2, dx + 6, y2, { c: ACC, w: 1.4 }) +
      t(dx - 12, (y1 + y2) / 2 - 2, lab, { size: 11, weight: 700, fill: ACC, ls: 1, anchor: 'end' }) + t(dx - 12, (y1 + y2) / 2 + 13, val, { size: 11, weight: 600, fill: MUTED, font: MONO, anchor: 'end' });
  };
  svg += dim(0, 60, 'LEGS', '0.6 H') + dim(60, 140, 'TORSO', '0.8 H') + dim(140, 240, 'HEAD', '1.0 H');
  // head width
  const hy = lev(254);
  svg += ln(cx - 57 * sc, hy, cx + 57 * sc, hy, { c: ACC, w: 1.4 }) + ln(cx - 57 * sc, hy - 6, cx - 57 * sc, hy + 6, { c: ACC, w: 1.4 }) + ln(cx + 57 * sc, hy - 6, cx + 57 * sc, hy + 6, { c: ACC, w: 1.4 });
  svg += t(cx, hy - 10, 'HEAD WIDTH 1.14 H', { size: 11, weight: 700, fill: ACC, anchor: 'middle', ls: 1 });

  // measurement table
  const rows = [
    ['Total height', '2.4 H'],
    ['Head height (crest tip → chin)', '1.0 H'],
    ['Head width', '1.14 H'],
    ['Torso (no neck)', '0.8 H'],
    ['Legs incl. feet', '0.6 H'],
    ['Arm, shoulder → fingertip', '0.7 H'],
    ['Iris diameter', '0.33 H'],
    ['Eye / head width', '29 %'],
    ['Pupil / iris', '42 %'],
    ['Tail spiral diameter', '0.64 H'],
    ['Tail spiral turns', '1.75'],
    ['Fingers / toes', '3 + thumb / 3'],
  ];
  const tx0 = X + 452, ty0 = Y + 92;
  svg += t(tx0, ty0, 'MEASURES', { size: 12, weight: 700, ls: 1.6, fill: MUTED });
  rows.forEach(([k, v], i) => {
    const y = ty0 + 34 + i * 38;
    svg += t(tx0, y, k, { size: 13, weight: 500 }) + t(X + Wp - 28, y, v, { size: 13, weight: 700, anchor: 'end', font: MONO, fill: ACC });
    svg += ln(tx0, y + 13, X + Wp - 28, y + 13, { c: '#EFEDE9', w: 1 });
  });
  svg += t(tx0, ty0 + 34 + rows.length * 38 + 6, 'Silhouette: compact, balanced,', { size: 12, weight: 500, fill: MUTED });
  svg += t(tx0, ty0 + 34 + rows.length * 38 + 24, 'head ≈ 42 % of total height.', { size: 12, weight: 500, fill: MUTED });
}

/* ---------------------------------------------------------------- 3. expressions */
{
  const X = 40, Y = 845, Wp = 2320, Hp = 350;
  svg += rect(X, Y, Wp, Hp);
  svg += panelHead(X, Y, '3', 'FACIAL EXPRESSIONS', '· driven by eyes, brow ridges and mouth · head shape never changes');
  const list = [
    ['neutral', 'NEUTRAL / OBSERVANT', 'lids 12% · pupils centred'],
    ['curious', 'CURIOUS', 'one brow up · gaze up-right'],
    ['surprised', 'SURPRISED', 'eyes +10% · pupils 55%'],
    ['happy', 'HAPPY', 'lower lids up · open smile'],
    ['confused', 'CONFUSED', 'asymmetric brows · wavy mouth'],
    ['suspicious', 'SUSPICIOUS', 'heavy lids · side glance'],
    ['excited', 'EXCITED', 'wide eyes · big pupils · grin'],
    ['thoughtful', 'THOUGHTFUL', 'half lids · gaze up-left'],
  ];
  const sw = (Wp - 40) / 8;
  const sc = 1.62;
  list.forEach(([key, name, note], i) => {
    const cx = X + 20 + sw * i + sw / 2;
    const cy = Y + 178;
    if (i) svg += ln(X + 20 + sw * i, Y + 80, X + 20 + sw * i, Y + Hp - 30, { c: '#EFEDE9', w: 1.2 });
    svg += g(cx, cy + 190 * sc, sc, K.headFront(key));
    svg += t(cx, Y + Hp - 50, `${String(i + 1).padStart(2, '0')} · ${name}`, { size: 13.5, weight: 700, anchor: 'middle', ls: 1 });
    svg += t(cx, Y + Hp - 30, note, { size: 11, weight: 500, anchor: 'middle', fill: MUTED, font: MONO });
  });
}

/* ---------------------------------------------------------------- 4. anatomy */
{
  const X = 40, Y = 1220, Wp = 1560, Hp = 350;
  svg += rect(X, Y, Wp, Hp);
  svg += panelHead(X, Y, '4', 'ANATOMICAL CONSTRUCTION');
  const cap = (cx, label, sub) => t(cx, Y + Hp - 36, label, { size: 13, weight: 700, anchor: 'middle', ls: 1 }) + t(cx, Y + Hp - 17, sub, { size: 11, weight: 500, anchor: 'middle', fill: MUTED, font: MONO });
  const sep = (x) => ln(x, Y + 70, x, Y + Hp - 24, { c: '#EFEDE9', w: 1.2 });

  // a) faceted head wireframe with face numbers
  {
    const cx = X + 150, sc = 1.42, oy = Y + 84 + 240 * sc;
    const faces = K.HEAD_FACES;
    let body = faces.map((fc) => `<path d="${K.P(fc.pts)}" fill="${fc.fill}" opacity="0.28" stroke="${ACC}" stroke-width="0.9" stroke-linejoin="round"/>`).join('');
    body += `<path d="${K.P(K.HEAD_OUTLINE)}" fill="none" stroke="${ACC}" stroke-width="2.2" stroke-linejoin="round"/>`;
    faces.forEach((fc, i) => {
      const c = fc.pts.reduce((a, p) => [a[0] + p[0] / fc.pts.length, a[1] + p[1] / fc.pts.length], [0, 0]);
      body += `<text x="${c[0]}" y="${c[1] + 3}" font-family="${MONO}" font-size="7.5" font-weight="700" fill="${ACC}" text-anchor="middle">${i + 1}</text>`;
    });
    body += `<line x1="0" y1="-246" x2="0" y2="-134" stroke="#C0392B" stroke-width="0.9" stroke-dasharray="3 2"/>`;
    body += `<line x1="-64" y1="-182" x2="64" y2="-182" stroke="#2E6FB0" stroke-width="0.9" stroke-dasharray="3 2"/>`;
    body += `<line x1="-64" y1="-157" x2="64" y2="-157" stroke="#2E6FB0" stroke-width="0.9" stroke-dasharray="3 2"/>`;
    svg += g(cx, oy, sc, body);
    svg += t(cx + 98, oy - 182 * sc + 4, 'eye line', { size: 10.5, weight: 600, fill: '#2E6FB0', font: MONO });
    svg += t(cx + 98, oy - 157 * sc + 4, 'mouth', { size: 10.5, weight: 600, fill: '#2E6FB0', font: MONO });
    svg += cap(cx, 'POLYHEDRAL HEAD', '14 faces · axis · guides');
    svg += sep(X + 300);
  }
  // b) eye detail
  {
    const cx = X + 375, cy = Y + 175, sc = 2.6;
    svg += g(cx, cy, sc, K.eye(0, 0, { lt: 0, side: 1 }));
    svg += callout(cx + 15 * sc, cy - 13 * sc, cx + 76, cy - 50, 'socket turret');
    svg += callout(cx + 12 * sc, cy + 6 * sc, cx + 76, cy + 18, 'iris #F4B642');
    svg += callout(cx + 2, cy + 8, cx + 76, cy + 62, 'pupil 42% iris');
    svg += callout(cx - 4.6 * sc, cy - 5 * sc, cx + 76, cy - 86, '2 highlights', { anchor: 'start' });
    svg += cap(cx + 40, 'EYE', 'large · amber · expressive');
    svg += sep(X + 560);
  }
  // c) crest + dorsal ridge (side)
  {
    const cx = X + 700, sc = 0.95, ground = Y + Hp - 64;
    svg += g(cx, ground, sc, K.viewSide());
    svg += callout(cx - 4 * sc, ground - 236 * sc, cx + 72, ground - 246, 'triangular crest');
    svg += callout(cx - 40 * sc, ground - 196 * sc, cx - 66, ground - 206, 'occipital ridge', { anchor: 'end' });
    svg += callout(cx - 34 * sc, ground - 132 * sc, cx - 66, ground - 150, 'dorsal spikes', { anchor: 'end' });
    svg += cap(cx, 'CREST → DORSAL LINE', 'continuous, head to tail');
    svg += sep(X + 870);
  }
  // d) hand
  {
    const cx = X + 965, cy = Y + 112, sc = 4;
    svg += g(cx, cy, sc, K.hand(0, 0, 1, 0, 1));
    svg += callout(cx - 13 * sc, cy + 9 * sc, cx - 80, cy + 118, 'opposable thumb', { anchor: 'start' });
    svg += callout(cx + 8 * sc, cy + 15 * sc, cx + 56, cy + 98, '3 fingers');
    svg += callout(cx + 1 * sc, cy + 18 * sc, cx + 56, cy + 98, '');
    svg += callout(cx - 8 * sc, cy + 15 * sc, cx + 56, cy + 98, '');
    svg += cap(cx, 'HAND', '3 fingers + 1 thumb');
    svg += sep(X + 1090);
  }
  // e) feet
  {
    const cx = X + 1185, base = Y + 175, sc = 3;
    svg += g(cx, base, sc, K.footFront(0));
    svg += g(cx + 12, base + 92, sc * 0.9, K.footSide(0));
    svg += t(cx - 86, base - 40, 'front', { size: 10.5, weight: 600, fill: MUTED, font: MONO });
    svg += t(cx - 86, base + 56, 'side', { size: 10.5, weight: 600, fill: MUTED, font: MONO });
    svg += callout(cx + 10.5 * sc, base - 3 * sc, cx + 30, base - 62, '3 toes');
    svg += cap(cx, 'FOOT', '3 forward-facing toes');
    svg += sep(X + 1280);
  }
  // f) tail spiral
  {
    const cx = X + 1440, cy = Y + 165, sc = 2.2;
    const { r0, r1 } = K.SPIRAL;
    let body = K.tailPath([-66, 44], [-50, 40], [-28, 36], [0, 0], 90);
    body += `<circle cx="0" cy="0" r="${r0}" fill="none" stroke="#2E6FB0" stroke-width="0.6" stroke-dasharray="2 2"/>`;
    body += `<circle cx="0" cy="0" r="${r1 * 2}" fill="none" stroke="#2E6FB0" stroke-width="0.6" stroke-dasharray="2 2"/>`;
    body += `<path d="M ${r0 + 9} -10 A ${r0 + 9} ${r0 + 9} 0 0 0 10 ${-(r0 + 8)}" fill="none" stroke="${ACC}" stroke-width="0.9"/><path d="M 10 ${-(r0 + 8)} l 5 -3 M 10 ${-(r0 + 8)} l 5 3" stroke="${ACC}" stroke-width="0.9" fill="none"/>`;
    svg += g(cx, cy, sc, body);
    svg += t(cx - 140, cy - 74, 'counter-clockwise', { size: 11, weight: 600, fill: ACC, font: MONO });
    svg += t(cx - 140, cy - 59, 'inward', { size: 11, weight: 600, fill: ACC, font: MONO });
    svg += cap(cx, 'TAIL SPIRAL', 'Ø 0.64 H · 1.75 turns · tapered');
  }
}

/* ---------------------------------------------------------------- 5. visual identity */
{
  const X = 1630, Y = 1220, Wp = 730, Hp = 350;
  svg += rect(X, Y, Wp, Hp);
  svg += panelHead(X, Y, '5', 'VISUAL IDENTITY');
  const pal = [
    ['#1B5E3B', 'Crest · dorsal', 'dark green'],
    ['#4CAF6B', 'Body · limbs', 'mid green'],
    ['#C9D45B', 'Organic spots', 'yellow-green'],
    ['#EAD9B7', 'Belly · ventral', 'cream'],
    ['#F4B642', 'Iris', 'amber'],
    ['#5B3A2E', 'Outline · detail', 'dark brown'],
  ];
  pal.forEach(([hex, role, nm], i) => {
    const col = i % 3, row = Math.floor(i / 3);
    const x = X + 30 + col * 150, y = Y + 80 + row * 118;
    svg += `<circle cx="${x + 28}" cy="${y + 28}" r="26" fill="${hex}" stroke="${RULE}" stroke-width="1.5"/>`;
    svg += t(x + 64, y + 22, hex, { size: 12.5, weight: 700, font: MONO, fill: ACC });
    svg += t(x + 64, y + 39, nm, { size: 11.5, weight: 500, fill: MUTED });
    svg += t(x, y + 76, role, { size: 12, weight: 600 });
  });
  const nx = X + 492;
  svg += ln(nx - 18, Y + 80, nx - 18, Y + Hp - 26, { c: '#EFEDE9', w: 1.2 });
  svg += t(nx, Y + 92, 'STYLE', { size: 12, weight: 700, fill: MUTED, ls: 1.6 });
  const style = ['Stylized 3D cartoon', 'Geometric, angular forms', 'Faceted polyhedral head', 'Outline #5B3A2E · 2.2% H', 'Subtle textures, flat light'];
  style.forEach((s, i) => (svg += t(nx, Y + 116 + i * 20, '· ' + s, { size: 12, weight: 500 })));
  svg += t(nx, Y + 236, 'NEVER', { size: 12, weight: 700, fill: '#B5452F', ls: 1.6 });
  const never = ['clothing, shoes, bags', 'accessories or props', 'other finger / toe counts', 'palette or proportion drift'];
  never.forEach((s, i) => (svg += t(nx, Y + 260 + i * 20, '✕ ' + s, { size: 12, weight: 500 })));
}

/* ---------------------------------------------------------------- footer */
svg += t(48, Hh - 10, 'KUMO © character design reference — every illustration, animation and 3D model must match this sheet.', { size: 11, weight: 500, fill: MUTED, font: MONO });

const doc = `<svg xmlns="http://www.w3.org/2000/svg" width="${W}" height="${Hh}" viewBox="0 0 ${W} ${Hh}">
<title>Kumo — Character Model Sheet</title>
<defs>${K.defs}</defs>
<rect width="${W}" height="${Hh}" fill="${BG}"/>
${svg}
</svg>`;

fs.mkdirSync(out, { recursive: true });
fs.writeFileSync(path.join(out, 'kumo-model-sheet.svg'), doc);
console.log('wrote', path.join(out, 'kumo-model-sheet.svg'));
