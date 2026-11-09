// Composes the cel-shaded (2.5D) Kumo sheet from the Blender renders.
// Usage: node build_sheet.mjs   (after `kumo_toon.py --render`)
// Writes ../kumo-toon-sheet.svg (references ./renders/*.png).
import fs from 'node:fs';
import path from 'node:path';

const ROOT = path.resolve(path.dirname(new URL(import.meta.url).pathname), '..');
const W = 2400;
const H = 1520;
const ACC = '#5B3A2E';
const TXT = '#2E2A27';
const MUTED = '#8A8580';
const RULE = '#E2E1DD';
const SANS = "Inter, 'Helvetica Neue', Arial, sans-serif";
const MONO = "'JetBrains Mono', 'DejaVu Sans Mono', monospace";
const t = (x, y, s, o = {}) =>
  `<text x="${x}" y="${y}" font-family="${o.font ?? SANS}" font-size="${o.size ?? 14}" font-weight="${o.weight ?? 500}" fill="${o.fill ?? TXT}" text-anchor="${o.anchor ?? 'start'}" letter-spacing="${o.ls ?? 0}">${s}</text>`;
const rect = (x, y, w, h) => `<rect x="${x}" y="${y}" width="${w}" height="${h}" rx="12" fill="#fff" stroke="${RULE}" stroke-width="1.5"/>`;
const head = (x, y, n, title, sub = '') =>
  `<circle cx="${x + 26}" cy="${y + 30}" r="15" fill="${ACC}"/>` +
  t(x + 26, y + 35.5, n, { size: 15, weight: 700, fill: '#fff', anchor: 'middle' }) +
  t(x + 52, y + 36, title, { size: 19, weight: 700, ls: 1.6 }) +
  (sub ? t(x + 52 + title.length * 15.6 + 14, y + 36, sub, { size: 13, fill: MUTED }) : '');
const img = (f, x, y, w, h) => `<image href="renders/${f}" x="${x}" y="${y}" width="${w}" height="${h}"/>`;

let s = '';
s += t(48, 92, 'KUMO', { size: 64, weight: 800, fill: ACC, ls: 4 });
s += `<line x1="268" y1="44" x2="268" y2="104" stroke="${RULE}" stroke-width="2"/>`;
s += t(292, 70, 'CEL-SHADED 2.5D MODEL', { size: 24, weight: 700, ls: 2.4 });
s += t(292, 98, 'Blender model · toon shading (3 hard light bands) · dark-brown outlines · for 3D and 2D animation', { size: 14.5, fill: MUTED });
s += t(2352, 70, 'kumo_toon.blend', { size: 14, weight: 700, anchor: 'end', font: MONO, fill: ACC });
s += t(2352, 96, 'ORTHOGRAPHIC · 1 H = HEAD HEIGHT · TOTAL 1.96 H', { size: 11.5, anchor: 'end', font: MONO, fill: MUTED });

// turnaround: the four renders share camera scale and ground line, so they are placed at one size
{
  const X = 40, Y = 130, Wp = 2320, Hp = 760;
  s += rect(X, Y, Wp, Hp) + head(X, Y, '1', 'TURNAROUND', '· same orthographic scale and ground line');
  const size = 660;
  const views = [['view-front.png', 'FRONT', '0°'], ['view-three-quarter.png', '3/4', '40°'], ['view-side.png', 'SIDE', '90°'], ['view-back.png', 'BACK', '180°']];
  const sw = (Wp - 40) / 4;
  views.forEach(([f, n, d], i) => {
    const cx = X + 20 + sw * i + sw / 2;
    s += img(f, cx - size / 2, Y + 50, size, size);
    s += t(cx, Y + Hp - 34, `${n} VIEW`, { size: 15, weight: 700, anchor: 'middle', ls: 1.6 });
    s += t(cx, Y + Hp - 14, `rotation ${d}`, { size: 11.5, anchor: 'middle', fill: MUTED, font: MONO });
  });
}
// expressions
{
  const X = 40, Y = 915, Wp = 2320, Hp = 400;
  s += rect(X, Y, Wp, Hp) + head(X, Y, '2', 'FACIAL EXPRESSIONS', '· pupils, flat 2.5D lids, brow ridges and mouth · head unchanged');
  const ex = [['neutral', 'NEUTRAL / OBSERVANT'], ['curious', 'CURIOUS'], ['surprised', 'SURPRISED'], ['happy', 'HAPPY'], ['confused', 'CONFUSED'], ['suspicious', 'SUSPICIOUS'], ['excited', 'EXCITED'], ['thoughtful', 'THOUGHTFUL']];
  const sw = (Wp - 40) / 8;
  const size = 272;
  ex.forEach(([k, n], i) => {
    const cx = X + 20 + sw * i + sw / 2;
    s += `<clipPath id="c${i}"><rect x="${cx - size / 2}" y="${Y + 66}" width="${size}" height="${size * 0.86}"/></clipPath>`;
    s += `<g clip-path="url(#c${i})">${img(`expr-${k}.png`, cx - size / 2, Y + 66, size, size)}</g>`;
    s += t(cx, Y + Hp - 28, `${String(i + 1).padStart(2, '0')} · ${n}`, { size: 13, weight: 700, anchor: 'middle', ls: 1 });
  });
}
// legend
{
  const Y = 1340;
  const items = [
    ['#4CAF6B', 'Body · 3 toon bands (shadow / mid / light)'],
    ['#1B5E3B', 'Crest diamond · occipital ridge · dorsal spikes'],
    ['#C9D45B', 'Angular camouflage patches'],
    ['#EAD9B7', 'Belly'],
    ['#F4B642', 'Iris · black vertical pupil'],
    ['#5B3A2E', 'Freestyle outline'],
  ];
  items.forEach(([c, l], i) => {
    const x = 60 + (i % 3) * 760;
    const y = Y + Math.floor(i / 3) * 50;
    s += `<circle cx="${x + 16}" cy="${y + 16}" r="15" fill="${c}" stroke="${RULE}" stroke-width="1.5"/>`;
    s += t(x + 44, y + 13, c, { size: 12, weight: 700, font: MONO, fill: ACC }) + t(x + 44, y + 31, l, { size: 12.5 });
  });
  s += t(48, H - 18, 'Built from the approved reference (referencia de modelo/). Regenerate: python kumo_toon.py --render, then node build_sheet.mjs.', { size: 11, fill: MUTED, font: MONO });
}

fs.writeFileSync(
  path.join(ROOT, 'kumo-toon-sheet.svg'),
  `<svg xmlns="http://www.w3.org/2000/svg" width="${W}" height="${H}" viewBox="0 0 ${W} ${H}"><title>Kumo — Cel-shaded 2.5D model</title><rect width="${W}" height="${H}" fill="#F5F5F3"/>${s}</svg>`,
);
console.log('built');
